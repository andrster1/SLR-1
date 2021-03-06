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
from models.VAE import VAE
from utils.trainUtils import train_vae
from utils.testUtils import test_vae
from datasets.CSL_Continuous_Openpose import CSL_Continuous_Openpose
from args import Arguments
from utils.ioUtils import *
from utils.textUtils import *
from torch.utils.tensorboard import SummaryWriter
from utils.collateUtils import skeleton_collate
import warnings
 
warnings.filterwarnings('ignore')
# Path settings
skeleton_root = "/mnt/data/haodong/CSL_Continious_Skeleton"
train_list = "/home/liweijie/Data/public_dataset/train_list.txt"
val_list = "/home/liweijie/Data/public_dataset/val_list.txt"
# Hyper params
learning_rate = 1e-5
batch_size = 2
epochs = 1000
sample_size = 224
num_class = 500
length = 32
dropout = 0.2
# Options
store_name = 'VAE_isolated'
checkpoint = '/home/liweijie/projects/SLR/checkpoint/VAE_isolated_checkpoint.pth.tar'
log_interval = 100
device_list = '1'
output_path = 'obj/vae_generate_CSL'
is_csl = True
num_workers = 8

# Get arguments
args = Arguments()

# Use specific gpus
os.environ["CUDA_VISIBLE_DEVICES"]=device_list
# Device setting
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Use writer to record
writer = SummaryWriter(os.path.join('runs/', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))

best_prec1 = 0.0
start_epoch = 0

# Train with Transformer
if __name__ == '__main__':
    # Build dictionary
    dictionary = build_csl_dictionary()
    # Load data
    trainset = CSL_Continuous_Openpose(skeleton_root=skeleton_root,list_file=train_list,dictionary=dictionary,
        clip_length=length,is_normalize=False)
    devset = CSL_Continuous_Openpose(skeleton_root=skeleton_root,list_file=val_list,dictionary=dictionary,
        clip_length=length,is_normalize=False)
    print("Dataset samples: {}".format(len(trainset)+len(devset)))
    trainloader = DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True,
        collate_fn=skeleton_collate)
    testloader = DataLoader(devset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True,
        collate_fn=skeleton_collate)
    # Create model
    model = VAE(num_class,dropout=dropout).to(device)
    if checkpoint is not None:
        start_epoch, best_prec1 = resume_model(model,checkpoint)
    # Run the model parallelly
    if torch.cuda.device_count() > 1:
        print("Using {} GPUs".format(torch.cuda.device_count()))
        model = nn.DataParallel(model)
    # Create loss criterion & optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    # Start Test
    print("Test Started".center(60, '#'))
    for epoch in range(start_epoch, start_epoch+1):
        # Test the model
        test_vae(model, criterion, testloader, device, epoch, log_interval, output_path, is_csl)

    print("Test Finished".center(60, '#'))


