# @author Metro
# @time 2021/11/3

"""
  Ref: https://github.com/cycraig/MP-DQN/blob/master/agents/pdqn.py
       https://github.com/AI4Finance-Foundation/ElegantRL/blob/master/elegantrl/net.py
"""

import torch
import torch.nn as nn
import numpy as np


def init_(m):
    if isinstance(m, nn.Linear):
        nn.init.kaiming_normal_(m.weight)
        nn.init.zeros_(m.bias)


class DuelingDQN(nn.Module):

    def __init__(self, state_dim, action_dim, hidden_layers=(256, 128, 64),
                 ):
        """

        :param state_dim:
        :param action_dim:
        :param hidden_layers:
        """
        super().__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim

        # initialize layers
        self.layers = nn.ModuleList()
        self.layers.append(nn.Linear(self.state_dim + self.action_dim, hidden_layers[0]))
        self.layers.append(nn.ReLU())
        for i in range(1, len(hidden_layers)):
            self.layers.append(nn.Linear(hidden_layers[i - 1], hidden_layers[i]))
            self.layers.append(nn.ReLU())
        self.adv_layers = nn.Sequential(nn.Linear(hidden_layers[-1], self.action_dim))
        self.val_layers = nn.Sequential(nn.Linear(hidden_layers[-1], 1))

        self.apply(init_)

    def forward(self, state, action_params):
        # batch_size = x.size(0)
        x = torch.cat((state, action_params), dim=1)
        for i in range(len(self.layers)):
            x = self.layers[i](x)
        adv = self.adv_layers(x)
        val = self.val_layers(x)

        return val + adv - adv.mean(dim=1, keepdim=True)

    def get_q1_q2(self, state, action_params):
        q_duel1 = self.forward(state, action_params)
        q_duel2 = self.forward(state, action_params)

        return q_duel1, q_duel2


class GaussianPolicy(nn.Module):

    def __init__(self, state_dim, action_dim, hidden_layers=(256, 128, 64), action_space=None,
                 ):
        """

        :param state_dim:
        :param action_dim:
        :param hidden_layers:
        """
        super().__init__()

        self.state_dim = state_dim
        self.action_dim = action_dim

        # initialize layers
        self.layers = nn.ModuleList()
        self.layers.append(nn.Linear(state_dim, hidden_layers[0]))
        self.layers.append(nn.ReLU())
        for i in range(1, len(hidden_layers)):
            self.layers.append(nn.Linear(hidden_layers[i - 1], hidden_layers[i]))
            self.layers.append(nn.ReLU())
        self.mean_layers = nn.Sequential(nn.Linear(hidden_layers[-1], self.action_dim))
        self.std_layers = nn.Sequential(nn.Linear(hidden_layers[-1], self.action_dim))

        self.soft_plus = nn.Softplus()
        self.apply(init_)

        # action rescaling
        if action_space is None:
            self.action_scale = torch.tensor(1.)
            self.action_bias = torch.tensor(0.)
        else:
            self.action_scale = torch.FloatTensor(
                (action_space.high - action_space.low) / 2.)
            self.action_bias = torch.FloatTensor(
                (action_space.high + action_space.low) / 2.)

    def forward(self, state):
        x = state
        for i in range(len(self.layers)):
            x = self.layers[i](x)
        a_mean = self.mean_layers(x)
        a_std_log = self.std_layers(x).clamp(-20, 2)
        return a_mean, a_std_log

    def get_action(self, state):
        x = state
        for i in range(len(self.layers)):
            x = self.layers[i](x)
        a_mean = self.mean_layers(x)
        a_std = self.std_layers(x).clamp(-20, 2).exp()
        return self.action_scale * torch.normal(a_mean, a_std).tanh() + self.action_bias # re-parameterize

    def get_action_logprob(self, state):
        a_mean, a_std_log = self.forward(state)
        a_std = a_std_log.exp()

        noise = torch.randn_like(a_mean, requires_grad=True)
        a_noise = a_mean + a_std * noise

        action = self.action_scale * torch.tanh(a_noise) + self.action_bias

        log_prob = a_std_log + np.log(np.sqrt(2 * np.pi)) + noise.pow(2).__mul__(0.5)
        log_prob += (np.log(2.) - a_noise - self.soft_plus(-2. * a_noise)) * 2.
        log_prob = log_prob.sum(1, keepdim=True)

        return action, log_prob
