#!/usr/bin/env python
"""
Quick Zimbabwe License Plate Trainer
=====================================

This script helps you quickly train a Zimbabwe-specific license plate detector
using transfer learning with a pre-trained model.

Requirements:
- pip install ultralytics
- At least 50-100 annotated Zimbabwe license plate images

Usage:
1. Organize your data in YOLO format
2. Run this script: python quick_zimbabwe_trainer.py
3. The trained model will be saved and integrated into the ANPR system
"""

import os
import sys
import yaml
from pathlib import Path

def setup_zimbabwe_training():
    """Set up training environment for Zimbabwe license plates"""
    
    print("🇿🇼 Zimbabwe License Plate Trainer Setup")
    print("=" * 50)
    
    # Check if ultralytics is installed
    try:
        from ultralytics import YOLO
        print("✅ YOLOv8 is available")
    except ImportError:
        print("❌ YOLOv8 not found. Installing...")
        os.system("pip install ultralytics")
        from ultralytics import YOLO
        print("✅ YOLOv8 installed successfully")
    
    # Create directory structure
    base_dir = Path("zimbabwe_plate_training")
    base_dir.mkdir(exist_ok=True)
    
    directories = [
        "images/train",
        "images/val", 
        "images/test",
        "labels/train",
        "labels/val",
        "labels/test"
    ]
    
    for dir_path in directories:
        (base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    # Create dataset configuration
    dataset_config = {
        'path': str(base_dir.absolute()),
        'train': 'images/train',
        'val': 'images/val',
        'test': 'images/test',
        'names': {
            0: 'zimbabwe_plate'
        },
        'nc': 1
    }
    
    config_path = base_dir / "zimbabwe_plates.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(dataset_config, f, default_flow_style=False)
    
    print(f"📁 Created training directory: {base_dir}")
    print(f"📝 Created config file: {config_path}")
    
    return base_dir, config_path

def create_sample_training_data(base_dir):
    """Create sample training data for demonstration"""
    import cv2
    import numpy as np
    
    print("\n🎨 Creating sample Zimbabwe license plate images...")
    
    # Zimbabwe plate colors and formats
    plate_formats = [
        "ABH 2411",
        "CAA 1234", 
        "ZBC 5678",
        "HAR 9012",
        "BUL 3456"
    ]
    
    for i, plate_text in enumerate(plate_formats):
        # Create yellow background (Zimbabwe plates are yellow)
        img = np.full((120, 300, 3), (0, 200, 255), dtype=np.uint8)  # Yellow in BGR
        
        # Add black border
        cv2.rectangle(img, (5, 5), (295, 115), (0, 0, 0), 2)
        
        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        thickness = 2
        color = (0, 0, 0)  # Black text
        
        # Calculate text size and position
        text_size = cv2.getTextSize(plate_text, font, font_scale, thickness)[0]
        text_x = (300 - text_size[0]) // 2
        text_y = (120 + text_size[1]) // 2
        
        cv2.putText(img, plate_text, (text_x, text_y), font, font_scale, color, thickness)
        
        # Save image
        img_path = base_dir / "images" / "train" / f"sample_{i:03d}.jpg"
        cv2.imwrite(str(img_path), img)
        
        # Create corresponding label (full plate bounding box)
        # YOLO format: class_id x_center y_center width height (normalized)
        label_content = "0 0.5 0.5 0.95 0.85\n"  # Almost full image
        
        label_path = base_dir / "labels" / "train" / f"sample_{i:03d}.txt"
        with open(label_path, 'w') as f:
            f.write(label_content)
    
    print(f"✅ Created {len(plate_formats)} sample training images")

def train_zimbabwe_model(config_path):
    """Train the Zimbabwe license plate detection model"""
    from ultralytics import YOLO
    
    print("\n🚀 Starting Zimbabwe license plate training...")
    
    # Load pre-trained YOLOv8 nano model (fastest for testing)
    model = YOLO('yolov8n.pt')
    
    print("📥 Pre-trained model loaded")
    
    # Train the model
    print("🎯 Training model...")
    results = model.train(
        data=str(config_path),
        epochs=50,  # Reduced for quick training
        imgsz=640,
        batch=4,   # Small batch for limited data
        patience=10,
        save_period=10,
        plots=True,
        verbose=True
    )
    
    print("✅ Training completed!")
    
    # Test the model
    print("\n🧪 Testing model...")
    validation_results = model.val()
    
    print(f"📊 Validation mAP50: {validation_results.box.map50:.3f}")
    print(f"📊 Validation mAP50-95: {validation_results.box.map:.3f}")
    
    # Save the model
    model_path = "zimbabwe_plate_detector.pt"
    model.save(model_path)
    
    print(f"💾 Model saved as: {model_path}")
    
    return model, model_path

def integrate_with_anpr(model_path):
    """Integrate trained model with existing ANPR system"""
    
    integration_code = f'''
# Add this to your detector.py file:

class ZimbabweYOLODetector:
    def __init__(self, model_path="{model_path}"):
        from ultralytics import YOLO
        self.model = YOLO(model_path)
    
    def detect_zimbabwe_plates(self, image):
        results = self.model(image)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    
                    if confidence > 0.5:  # Confidence threshold
                        x, y = int(x1), int(y1)
                        w, h = int(x2 - x1), int(y2 - y1)
                        detections.append((x, y, w, h))
        
        return detections

# Usage in your main detection function:
zimbabwe_detector = ZimbabweYOLODetector()
zimbabwe_regions = zimbabwe_detector.detect_zimbabwe_plates(image)
'''
    
    print("\n🔧 Integration code:")
    print(integration_code)
    
    # Save integration code to file
    with open("zimbabwe_integration.py", 'w') as f:
        f.write(integration_code)
    
    print("💾 Integration code saved to: zimbabwe_integration.py")

def main():
    """Main training pipeline"""
    print("🇿🇼 Quick Zimbabwe License Plate Trainer")
    print("========================================")
    
    # Setup training environment
    base_dir, config_path = setup_zimbabwe_training()
    
    # Create sample data (you should replace this with real data)
    create_sample_training_data(base_dir)
    
    print("\n📋 Next Steps:")
    print(f"1. Replace sample images in {base_dir}/images/train/ with real Zimbabwe plate images")
    print(f"2. Replace sample labels in {base_dir}/labels/train/ with proper annotations")
    print("3. Run training again with: python -c 'from quick_zimbabwe_trainer import train_zimbabwe_model; train_zimbabwe_model(\"zimbabwe_plate_training/zimbabwe_plates.yaml\")'")
    
    # Ask user if they want to train with sample data
    response = input("\n❓ Train with sample data now? (y/n): ").lower().strip()
    
    if response == 'y':
        try:
            model, model_path = train_zimbabwe_model(config_path)
            integrate_with_anpr(model_path)
            
            print("\n🎉 Zimbabwe license plate detector trained successfully!")
            print(f"📁 Model saved at: {model_path}")
            print("🔧 Check zimbabwe_integration.py for integration code")
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
            print("💡 Make sure you have sufficient training data and proper labels")
    else:
        print("\n👍 Setup complete! Add your training data and run training when ready.")

if __name__ == "__main__":
    main()
