import argparse
from pickle import TRUE

from Architecture.generator import AE

import torch
import torch.nn as nn
import os
import numpy as np
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm
import matplotlib.pyplot as plt
from torchmetrics.classification import BinaryROC
from torchmetrics import ROC
from torchmetrics.functional.classification import binary_roc


def options():
    # Arguments to pass from terminal to make our lives easier
    parser = argparse.ArgumentParser(description='Training of AE')
    parser.add_argument('--arch', 
                        dest='arch', 
                        type=str, 
                        help="Architecture of the model Eg: 1,2,3,4")

    return parser.parse_args()


args = options()


# Loading Features
FeatsPath = "/shared/home/v_varenyam_bhardwaj/local_scratch/Dataset/FeaturesResnext/"
feats_complete_test = np.load(FeatsPath + "anomalous_test_set_video_features.npy", allow_pickle=True)
feats_normal_test = np.load(FeatsPath + "all_test_set_video_features.npy", allow_pickle=True)

# Defining Device
try:
    device = torch.device("cuda:0")
except:
    device = torch.device("cpu")

# from AutoEncoder import AE
arch = [int(i) for i in args.arch.split(',')]
model = AE(arch).to(device)

model_name = "AE_"
for i in arch:
    model_name += str(i) + "_"

model_name = model_name[:-1]
model.load_state_dict(torch.load('SavedModels/AE/{}.pth'.format(model_name)))

device = "cuda:3" if torch.cuda.is_available() else "cpu"
# print("Device in use is {}".format(device))
torch.manual_seed(18)

model = model.to(device)

transform = transforms.Compose([
    transforms.ToTensor()
    ])


normal_test_dataset = DataLoader(feats_normal_test, batch_size = 1, shuffle = False)
complete_test_dataset = DataLoader(feats_complete_test, batch_size = 1, shuffle = False)


criterion = nn.MSELoss()


best_loss = 1e10
epochs = 1

loss_values_test = []
normal_predictions = []
anomalous_predictions = []

for epoch in range(epochs):

    # on test set normal
    
    test_loss_normal = 0
    model.eval()
    with torch.no_grad():
        for idx, img in tqdm(enumerate(normal_test_dataset)):

            img = img.to(device)

            prediction = model(img)

            loss = criterion(prediction, img)
            test_loss_normal += loss.item() * img.size(0)
            normal_predictions.append(loss.item())

    test_loss_normal /= len(normal_test_dataset)

    loss_values_test.append(test_loss_normal)
    print("Test Loss Normal: {}".format(test_loss_normal))


    # on test set anomalous
    complete_test_loss = 0
    model.eval()
    with torch.no_grad():
        for idx, img in tqdm(enumerate(complete_test_dataset)):

            img = img.to(device)
            prediction = model(img)

            loss = criterion(prediction, img)
            complete_test_loss += loss.item() * img.size(0)
            anomalous_predictions.append(loss.item())

    complete_test_loss /= len(complete_test_dataset)
    loss_values_test.append(complete_test_loss)
    print("Test Loss Complete: {}".format(complete_test_loss))


np.save('Losses/AE/Test_Loss_{}.npy'.format(model_name), loss_values_test)
normal_predictions = torch.tensor(normal_predictions)
print(normal_predictions)
np.squeeze(normal_predictions)
anomalous_predictions = torch.tensor(anomalous_predictions)

temp = np.load(FeatsPath + 'anomalous_test_set_labels_segment_level.npy', allow_pickle=True)
new = []
for i in temp:
    for j in i:
        new.append(j)

test_feats_anomolous_labels = torch.tensor(new)

temp = np.load(FeatsPath + '/normal_test_set_labels_segment_level.npy', allow_pickle=True)

new = []
for i in temp:
    for j in i:
        new.append(j)

feats_normal_test_labels = torch.tensor(new)

# roc = roc(num_classes=1)
fpr, tpr, thresholds = binary_roc(anomalous_predictions, test_feats_anomolous_labels)
print("Thresholds are: ", thresholds)


plt.figure(figsize=(5,5))
plt.title("ROC")
plt.plot(fpr,tpr)
plt.xlabel("fpr")
plt.ylabel("tpr")
plt.savefig('ROC/AE/ROC_{}.png'.format(model_name))