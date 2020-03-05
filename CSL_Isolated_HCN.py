import os
import sys
import time
from datetime import datetime
import logging
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import torchvision.transforms as transforms
from models.fHCN import fHCN
from utils.trainUtils import train_isolated
from utils.testUtils import test_isolated
from datasets.CSL_Isolated import CSL_Isolated
from args import Arguments
from utils.ioUtils import save_checkpoint, resume_model
from utils.critUtils import LabelSmoothing
from utils.textUtils import build_dictionary, reverse_dictionary
from torch.utils.tensorboard import SummaryWriter

# Path settings
video_root = "/home/liweijie/SLR_dataset/S500_color_video"
skeleton_root = "/home/liweijie/skeletons_dataset"
train_file = "input/train_list.txt"
val_file = "input/val_list.txt"
# Hyper params
learning_rate = 1e-5
batch_size = 8
epochs = 1000
sample_size = 224
num_class = 500
# Options
store_name = 'fHCN_isolated'


# Get arguments
args = Arguments()

# Use specific gpus
os.environ["CUDA_VISIBLE_DEVICES"]=args.device_list
# Device setting
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Use writer to record
writer = SummaryWriter(os.path.join('runs/', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))

best_prec1 = 0.0
start_epoch = 0

# Train with Transformer
if __name__ == '__main__':
    # Load data
    transform = transforms.Compose([transforms.Resize([sample_size, sample_size]),
                                    transforms.ToTensor(),
                                    transforms.Normalize(mean=[0.5], std=[0.5])])
    trainset = CSL_Isolated(video_root=video_root,skeleton_root=skeleton_root,list_file=train_file,
        transform=transform)
    devset = CSL_Isolated(video_root=video_root,skeleton_root=skeleton_root,list_file=val_file,
        transform=transform)
    print("Dataset samples: {}".format(len(trainset)+len(devset)))
    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=1, pin_memory=True)
    testloader = DataLoader(devset, batch_size=batch_size, shuffle=False, num_workers=1, pin_memory=True)
    # Create model
    model = fHCN(num_class).to(device)
    if resume_model is not None:
        start_epoch, best_prec1 = resume_model(model,resume_model)
    # Run the model parallelly
    if torch.cuda.device_count() > 1:
        print("Using {} GPUs".format(torch.cuda.device_count()))
        model = nn.DataParallel(model)
    # Create loss criterion & optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Start training
    print("Training Started".center(60, '#'))
    for epoch in range(start_epoch, epochs):
        # Train the model
        train_isolated(model, criterion, optimizer, trainloader, device, epoch, logger, args.log_interval, writer, reverse_dict)
        # Test the model
        prec1 = test_isolated(model, criterion, testloader, device, epoch, logger, args.log_interval, writer, reverse_dict)
        # Save model
        # remember best prec1 and save checkpoint
        is_best = prec1>best_prec1
        best_prec1 = min(prec1, best_prec1)
        save_checkpoint({
            'epoch': epoch + 1,
            'state_dict': model.state_dict(),
            'best': best_prec1
        }, is_best, args.model_path, store_name)
        print("Epoch {} Model Saved".format(epoch+1).center(60, '#'))

    print("Training Finished".center(60, '#'))
