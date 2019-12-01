import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import pandas as pd 
import json
import random
import argparse
import logging
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import sys
from sklearn.neighbors import KNeighborsClassifier

parser = argparse.ArgumentParser()
parser.add_argument('--config', type=str, required=True)
args = parser.parse_args()
with open(args.config, 'r') as f:
    args = json.load(f)


def load_data():
    data = pd.read_csv('../features/rescaling.csv')
    data.loc[data.label == 'patches', 'label'] = 0
    data.loc[data.label == 'scratches', 'label'] = 1
    # print(data)
    train_X, test_X, train_Y, test_Y = train_test_split(data[data.columns[0:6]].values, data.label.values, test_size=0.2, random_state=1)
    # print(train_X)
    train_len = np.size(train_X, 0)
    test_len = np.size(test_X, 0)
    total_len = train_len + test_len

    print('Data loaded! , total len:{0}, train len:{1}, test len:{2}'.format(total_len, train_len, test_len))

    return train_X, test_X, train_Y, test_Y


class MLP(nn.Module):
    def __init__(self, config): 
        super(MLP, self).__init__()
        option = config['mlp']
        drop_prob = option['dropout']
        hidden_size = option['hidden_size']
        
        self.fc1 = nn.Linear(config['input_size'], hidden_size)
        self.converter1 = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.converter2 = nn.ReLU()
        self.fc3 = nn.Linear(hidden_size, config['num_labels'])
        self.dropout = nn.Dropout(drop_prob)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, features):
        X = self.converter1(self.fc1(features))
        X = self.converter2(self.fc2(X))
        # X = self.dropout(X)
        X = self.fc3(X)
        # print(X)
        X = self.softmax(X)
        
        return X


def train_MLP():
    random.seed(args['seed'])
    np.random.seed(args['seed'])
    torch.manual_seed(args['seed'])

    train_X, test_X, train_Y, test_Y = load_data()

    train_labels = train_Y
    test_labels = test_Y

    train_X = torch.from_numpy(train_X).float().cuda()
    test_X = torch.from_numpy(test_X).float().cuda()
    train_Y = torch.from_numpy(train_Y).long().cuda()
    test_Y = torch.from_numpy(test_Y).long().cuda()



    model = MLP(args).cuda()

    cross_entropy_loss = nn.CrossEntropyLoss()

    optimizer = optim.Adam(model.parameters(), lr=args['lr'])


    print("============start trainning==============")
    
    for epoch in range(args['num_epochs']):
        loss_value, train_acc = 0.0, 0.0
        optimizer.zero_grad()
        out = model(train_X)
        loss = cross_entropy_loss(out, train_Y) 
        loss.backward()
        optimizer.step()

        train_predict_out = out.cpu()
        _, train_predict_label = torch.max(train_predict_out, 1)
        train_acc = accuracy_score(train_labels, train_predict_label.data)

        test_predict_out = model(test_X)
        test_predict_out = test_predict_out.cpu()
        _, test_predict_label = torch.max(test_predict_out, 1)
        test_acc = accuracy_score(test_labels, test_predict_label.data)

        if (epoch + 1) % 50 == 0:
            loss_value = loss.item()
            print('epoch %.3d, loss %.4f, train acc %.3f, test acc %.3f'
                % (epoch + 1, loss_value, train_acc, test_acc))
    
    print("============trainning end==============")
    predict_out = model(test_X)
    predict_out = predict_out.cpu()
    _, predict_label = torch.max(predict_out, 1)
    test_Y.data = test_Y.data.cpu()
    accuracy = accuracy_score(test_Y.data, predict_label.data)
    print ('MLP prediction accuracy: ', accuracy)
    op = args['mlp']
    torch.save(model, "../save_model/rescaling_mlp_" + str(accuracy) + "_" + str(op['hidden_size']) + "_" + str(args['lr']))

def load_MLP():
    train_X, test_X, train_Y, test_Y = load_data()

    train_X = torch.from_numpy(train_X).float().cuda()
    test_X = torch.from_numpy(test_X).float().cuda()
    train_Y = torch.from_numpy(train_Y).long().cuda()
    test_Y = torch.from_numpy(test_Y).long().cuda()

    model = torch.load(args['model'])
    model.eval()
    predict_out = model(test_X)
    predict_out = predict_out.cpu()
    _, predict_label = torch.max(predict_out, 1)
    test_Y.data = test_Y.data.cpu()
    accuracy = accuracy_score(test_Y.data, predict_label.data)
    print ('MLP prediction accuracy: ', accuracy)

def knn():
    option = args['knn']
    classfier = KNeighborsClassifier(option['k'])
    train_X, test_X, train_Y, test_Y = load_data()
    classfier.fit(train_X, train_Y)
    predict_label = classfier.predict(test_X)
    accuracy = accuracy_score(test_Y.data, predict_label.data)
    print ('KNN prediction accuracy: ', accuracy)


def main():
    if args['type'] == 'mlp' and args['load'] == False:
        train_MLP()
    elif args['type'] == 'mlp' and args['load'] == True:
        load_MLP()
    elif args['type'] == 'knn':
        knn()

if __name__ == '__main__':
    main()
    