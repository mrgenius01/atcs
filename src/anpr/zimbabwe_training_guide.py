"""
Zimbabwe License Plate Detection Training Guide
============================================

This guide will help you train a custom YOLO model specifically for Zimbabwe license plates.

STEP 1: Dataset Collection
-------------------------
You need to collect 500-2000 images of Zimbabwe license plates with the following characteristics:

Zimbabwe License Plate Format:
- Standard format: ABC 1234 (3 letters, 4 numbers)
- Alternative: AB 1234 CD (2 letters, 4 numbers, 2 letters)
- Colors: Yellow background with black text
- Dimensions: Approximately 520mm x 110mm

Dataset Requirements:
- Various lighting conditions (day, night, shadows)
- Different angles (front view, slight angles)
- Different distances (close-up, medium, far)
- Various backgrounds (urban, rural, parking lots)
- Weather conditions (sunny, cloudy, rainy)

STEP 2: Image Annotation
-----------------------
Use one of these tools to annotate your images:
- LabelImg (recommended): https://github.com/heartexlabs/labelImg
- Roboflow: https://roboflow.com/
- CVAT: https://cvat.org/

Annotation Guidelines:
- Draw tight bounding boxes around each license plate
- Label class as "license_plate" or "zw_plate"
- Include partially visible plates
- Don't include severely blurred/unreadable plates

STEP 3: Dataset Structure
------------------------
Organize your dataset like this:

zimbabwe_plates/
├── images/
│   ├── train/          (70% of images)
│   ├── val/            (20% of images)
│   └── test/           (10% of images)
├── labels/
│   ├── train/          (corresponding .txt files)
│   ├── val/
│   └── test/
└── dataset.yaml

STEP 4: YOLO Training Configuration
----------------------------------
"""

import os
import yaml

def create_yolo_config():
    """Create YOLO training configuration for Zimbabwe plates"""
    
    # Dataset configuration
    dataset_config = {
        'path': 'zimbabwe_plates',
        'train': 'images/train',
        'val': 'images/val', 
        'test': 'images/test',
        'names': {
            0: 'license_plate'
        },
        'nc': 1  # number of classes
    }
    
    # Training configuration
    training_config = {
        'model': 'yolov8n.pt',  # Start with nano model for faster training
        'data': 'zimbabwe_plates.yaml',
        'epochs': 100,
        'imgsz': 640,
        'batch': 16,
        'device': 0,  # Use GPU if available
        'patience': 20,
        'save_period': 10,
        'workers': 4,
        'optimizer': 'SGD',
        'lr0': 0.01,
        'momentum': 0.937,
        'weight_decay': 0.0005,
        'warmup_epochs': 3.0,
        'box': 7.5,
        'cls': 0.5,
        'dfl': 1.5,
        'pose': 12.0,
        'kobj': 1.0,
        'label_smoothing': 0.0,
        'nbs': 64,
        'overlap_mask': True,
        'mask_ratio': 4,
        'dropout': 0.0,
        'val': True,
        'plots': True
    }
    
    return dataset_config, training_config

def create_training_script():
    """Generate training script for Zimbabwe license plates"""
    
    script = '''
#!/usr/bin/env python3
"""
Zimbabwe License Plate YOLO Training Script
"""

from ultralytics import YOLO
import torch

def train_zimbabwe_plate_detector():
    """Train YOLO model for Zimbabwe license plates"""
    
    print("Starting Zimbabwe License Plate Training...")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    # Load pre-trained YOLOv8 model
    model = YOLO('yolov8n.pt')
    
    # Train the model
    results = model.train(
        data='zimbabwe_plates.yaml',
        epochs=100,
        imgsz=640,
        batch=16,
        device=0 if torch.cuda.is_available() else 'cpu',
        patience=20,
        save_period=10,
        plots=True,
        verbose=True
    )
    
    # Validate the model
    validation_results = model.val()
    
    # Export the model
    model.export(format='onnx')
    
    print("Training completed!")
    print(f"Best weights saved to: runs/detect/train/weights/best.pt")
    
    return model, results

if __name__ == "__main__":
    train_zimbabwe_plate_detector()
'''
    return script

def create_data_augmentation_script():
    """Create data augmentation script to increase dataset size"""
    
    script = '''
import cv2
import numpy as np
import os
from pathlib import Path
import albumentations as A

def augment_zimbabwe_plates(input_dir, output_dir, augmentations_per_image=5):
    """
    Apply data augmentation to Zimbabwe license plate images
    """
    
    # Define augmentation pipeline
    transform = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.8),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15, val_shift_limit=10, p=0.7),
        A.GaussNoise(var_limit=(10.0, 50.0), p=0.5),
        A.MotionBlur(blur_limit=3, p=0.3),
        A.RandomGamma(gamma_limit=(80, 120), p=0.5),
        A.CLAHE(clip_limit=2.0, tile_grid_size=(8, 8), p=0.5),
        A.RandomShadow(shadow_roi=(0, 0.5, 1, 1), num_shadows_lower=1, num_shadows_upper=2, p=0.3),
        A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, alpha_coef=0.08, p=0.2),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    for img_file in input_path.glob('*.jpg'):
        image = cv2.imread(str(img_file))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Load corresponding label file
        label_file = input_path / f"{img_file.stem}.txt"
        if not label_file.exists():
            continue
            
        with open(label_file, 'r') as f:
            lines = f.readlines()
        
        bboxes = []
        class_labels = []
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                class_id = int(parts[0])
                x_center, y_center, width, height = map(float, parts[1:5])
                bboxes.append([x_center, y_center, width, height])
                class_labels.append(class_id)
        
        # Apply augmentations
        for i in range(augmentations_per_image):
            try:
                transformed = transform(image=image, bboxes=bboxes, class_labels=class_labels)
                
                aug_image = transformed['image']
                aug_bboxes = transformed['bboxes']
                aug_labels = transformed['class_labels']
                
                # Save augmented image
                output_img_file = output_path / f"{img_file.stem}_aug_{i}.jpg"
                cv2.imwrite(str(output_img_file), cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR))
                
                # Save augmented labels
                output_label_file = output_path / f"{img_file.stem}_aug_{i}.txt"
                with open(output_label_file, 'w') as f:
                    for bbox, label in zip(aug_bboxes, aug_labels):
                        f.write(f"{label} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\\n")
                        
            except Exception as e:
                print(f"Error augmenting {img_file}: {e}")
                continue
        
        print(f"Processed {img_file.name}")

if __name__ == "__main__":
    augment_zimbabwe_plates("original_images", "augmented_images")
'''
    return script

# Installation requirements
requirements = '''
# Zimbabwe License Plate Training Requirements
ultralytics>=8.0.0
torch>=1.9.0
torchvision>=0.10.0
opencv-python>=4.5.0
albumentations>=1.3.0
pyyaml>=6.0
matplotlib>=3.3.0
seaborn>=0.11.0
pandas>=1.3.0
numpy>=1.21.0
Pillow>=8.3.0
tqdm>=4.62.0
'''

print("YOLO Training Guide for Zimbabwe License Plates")
print("=" * 50)
print()
print("STEP 1: Install Requirements")
print("pip install ultralytics opencv-python albumentations")
print()
print("STEP 2: Collect and Annotate Images")
print("- Collect 500-2000 Zimbabwe license plate images")
print("- Use LabelImg to annotate bounding boxes")
print("- Save annotations in YOLO format")
print()
print("STEP 3: Create Dataset Structure")
print("- Split data: 70% train, 20% val, 10% test")
print("- Create dataset.yaml configuration")
print()
print("STEP 4: Train Model")
print("- Run the training script")
print("- Monitor training progress")
print("- Validate model performance")
print()
print("STEP 5: Deploy Trained Model")
print("- Export to ONNX format")
print("- Integrate with ANPR system")
print("- Test with real Zimbabwe plates")
