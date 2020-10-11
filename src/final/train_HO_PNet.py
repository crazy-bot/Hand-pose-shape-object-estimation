from config import *
import sys
sys.path.append(PROJECT_PATH)

import torch
import torch.nn as nn
import torch.optim as optim
import argparse
import os

from src.train_helper import train_HO_PNet,val_HO_PNet
from networks.HO_Nets.HO_Posenet import HO_Posenet
from dataset.HO_Data.HO_pose import Ho3DDataset

ap = argparse.ArgumentParser()
ap.add_argument("--load_ckpt", type=str, help="relative path to load checkpoint", default='')
ap.add_argument("--save_ckpt", type=str, help="relative path to save checkpoint", default='HO_PNet')
ap.add_argument("--multiGPU", type=bool, help="if multi GPU training needed", default=True)

args = ap.parse_args()
checkpoint_dir = os.path.join(CHECKPOINT_BASE, args.save_ckpt)
if not os.path.exists(checkpoint_dir): os.mkdir(checkpoint_dir)
#######################################################################################

################# Dataset and data loader ###############
print('==> Preparing data ..')
torch.manual_seed(1)
torch.cuda.manual_seed(1)

train_set = Ho3DDataset(root=DATA_DIR, pathFile='train.txt', augmentation=False, dtype=dtype)
val_set = Ho3DDataset(root=DATA_DIR, pathFile='valid.txt', augmentation=False, dtype=dtype, isValid=True)

train_loader = torch.utils.data.DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=0)
val_loader = torch.utils.data.DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=0)
print('train size--', len(train_loader))
print('val size--', len(val_loader))

#######################################################################################
###################### Model, criterion and optimizer ###########################
print('==> Constructing model .. HO_PNet')
net = HO_Posenet(input_channels=1, hand_channels=handpoints_num,obj_channels=objpoints_num)

if(args.multiGPU):
    net = nn.DataParallel(net)

net = net.to(device, dtype)
criterion = nn.MSELoss()
optimizer = optim.Adam(net.parameters(),lr=0.001)

#######################################################################################
################ load predefined checkpoint ###############
if args.load_ckpt is not '':
    checkpoint_file = os.path.join(CHECKPOINT_BASE, args.load_ckpt)
    print(checkpoint_file)
    assert os.path.isfile(checkpoint_file), 'Error: no checkpoint file of found '+checkpoint_file

    checkpoint = torch.load(checkpoint_file)
    net.load_state_dict(checkpoint['model_state_dict'])
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    start_epoch = checkpoint['epoch'] + 1


#######################################################################################
##################### Train and Validate #################
print('==> Training ..')
for epoch in range(start_epoch, start_epoch + epochs_num):
    print('Epoch: {}'.format(epoch))
    train_HO_PNet(net, criterion, optimizer, train_loader, device=device)
    val_HO_PNet(net, val_loader, device=device)

    if save_checkpoint and epoch % checkpoint_per_epochs == 0:

        checkpoint_file = os.path.join(checkpoint_dir, 'epoch'+str(epoch)+'.pth')
        checkpoint = {
            'model_state_dict': net.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, checkpoint_file)
