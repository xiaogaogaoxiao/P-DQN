# @author Metro
# @time 2021/11/3

"""
  Ref: https://github.com/cycraig/MP-DQN/blob/master/agents/pdqn.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DuelingDQN(nn.Module):

    def __init__(self, state_dim, action_dim, param_state_dim, adv_hidden_layers=(256, 128, 64),
                 val_hidden_layers=(256, 128, 64)):
        """

        :param state_dim:
        :param action_dim:
        :param param_state_dim:
        :param adv_hidden_layers:
        :param val_hidden_layers
        """
        super().__init__()
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.param_state_dim = param_state_dim

        # create layers
        self.adv_layers = nn.ModuleList()
        self.val_layers = nn.ModuleList()
        input_size = self.state_dim + self.param_state_dim

        # adv_layers
        self.adv_layers.append(nn.Linear(input_size, adv_hidden_layers[0]))
        for i in range(1, len(adv_hidden_layers)):
            self.adv_layers.append(nn.Linear(adv_hidden_layers[i - 1], adv_hidden_layers[i]))
        self.adv_layers.append(nn.Linear(adv_hidden_layers[-1], self.action_dim))

        # initialize adv_layer weights
        for i in range(0, len(self.adv_layers)):
            nn.init.kaiming_normal_(self.adv_layers[i].weight, nonlinearity='relu')
            nn.init.zeros_(self.adv_layers[i].bias)

        # val_layers
        self.val_layers.append(nn.Linear(input_size, val_hidden_layers[0]))
        for i in range(1, len(val_hidden_layers)):
            self.val_layers.append(nn.Linear(val_hidden_layers[i - 1], val_hidden_layers[i]))
        self.val_layers.append(nn.Linear(val_hidden_layers[-1], 1))

        # initialize val_layer weights
        for i in range(0, len(self.val_layers)):
            nn.init.kaiming_normal_(self.val_layers[i].weight, nonlinearity='relu')
            nn.init.zeros_(self.val_layers[i].bias)

    def forward(self, state, action_parameters):
        # batch_size = x.size(0)
        x = torch.cat((state, action_parameters), dim=1)

        adv = x
        for i in range(0, len(self.adv_layers) - 1):
            adv = F.relu(self.adv_layers[i](adv))
        adv = self.adv_layers[-1](adv)

        val = x
        for i in range(0, len(self.val_layers) - 1):
            val = F.relu(self.val_layers[i](val))
        val = self.val_layers[-1](val)

        return val + adv - adv.mean(dim=1, keepdim=True)


class ParamNet(nn.Module):

    def __init__(self, state_dim, param_state_dim, param_hidden_layers):
        """

        :param state_dim:
        :param param_state_dim:
        :param param_hidden_layers:
        """
        super(ParamNet, self).__init__()

        self.state_dim = state_dim
        self.param_state_dim = param_state_dim

        # create layers
        self.layers = nn.ModuleList()
        self.layers.append(nn.Linear(self.state_dim, param_hidden_layers[0]))
        for i in range(1, len(param_hidden_layers)):
            self.layers.append(nn.Linear(param_hidden_layers[i - 1], param_hidden_layers[i]))
        self.layers.append(nn.Linear(param_hidden_layers[-1], self.param_state_dim))

        # initialize layer weights
        for i in range(0, len(self.layers)):
            nn.init.kaiming_normal_(self.layers[i].weight, nonlinearity='relu')
            nn.init.zeros_(self.layers[i].bias)

    def forward(self, state):
        x = state
        for i in range(len(self.layers) - 1):
            x = F.relu(self.layers[i](x))

        return torch.sigmoid(self.layers[-1](x)) * 10 + 5