"""
Dataset Tools for SILS v1
Complete utilities for managing training datasets
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import Counter
import hashlib
import shutil
from datetime import datetime


class DatasetManager:
    """
    Complete dataset management system.
    
    Features:
    - Add new examples
    - Clean and deduplicate datasets
    - Merge multiple JSONL files
    - Export training-ready JSONL
    - Version control for datasets
    """
    
    def __init__(self, dataset_path: str):
        self.dataset_path = Path(dataset_path)
        self.dataset_dir = self.dataset_path.parent
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
    
    def add_example(self, input_text: str, output_text: str, 
                   intent_label: int = 0, tone_label: int = 0, 
                   metadata: Optional[Dict] = None):
        """
        Add a new example to the dataset.
        
        Args:
            input_text: User input
            output_text: AI response
            intent_label: Intent classification (0-5)
            tone_label: Tone classification (optional)
            metadata: Additional metadata
        """
        example = {
            'input': input_text.strip(),
            'output': output_text.strip(),
            'intent_label': intent_label,
            'tone_label': tone_label,
            'metadata': metadata or {}
        }
        
        # Append to dataset file
        with open(self.dataset_path, 'a') as f:
            f.write(json.dumps(example) + '\n')
        
        print(f"Added example to {self.dataset_path}")
    
    def add_batch(self, examples: List[Dict]):
        """
        Add multiple examples at once.
        
        Args:
            examples: List of example dicts
        """
        with open(self.dataset_path, 'a') as f:
            for example in examples:
                # Validate required fields
                if 'input' not in example or 'output' not in example:
                    print(f"Skipping invalid example: {example}")
                    continue
                
                # Set defaults
                example.setdefault('intent_label', 0)
                example.setdefault('tone_label', 0)
                example.setdefault('metadata', {})
                
                f.write(json.dumps(example) + '\n')
        
        print(f"Added {len(examples)} examples to {self.dataset_path}")
    
    def clean(self, output_path: Optional[str] = None, 
             remove_duplicates: bool = True,
             remove_empty: bool = True,
             remove_invalid: bool = True,
             min_input_length: int = 1,
             min_output_length: int = 1) -> Dict:
        """
        Clean the dataset.
        
        Args:
            output_path: Output file (if None, overwrites original)
            remove_duplicates: Remove duplicate examples
            remove_empty: Remove empty inputs/outputs
            remove_invalid: Remove malformed JSON
            min_input_length: Minimum input length in characters
            min_output_length: Minimum output length in characters
        
        Returns:
            Statistics dict
        """
        print(f"Cleaning dataset: {self.dataset_path}")
        
        examples = []
        seen_hashes = set()
        
        stats = {
            'total': 0,
            'duplicates': 0,
            'empty': 0,
            'invalid': 0,
            'too_short': 0,
            'kept': 0
        }
        
        # Read and clean
        with open(self.dataset_path, 'r') as f:
            for line in f:
                stats['total'] += 1
                
                if not line.strip():
                    continue
                
                try:
                    example = json.loads(line)
                except json.JSONDecodeError:
                    stats['invalid'] += 1
                    if remove_invalid:
                        continue
                
                # Check required fields
                if 'input' not in example or 'output' not in example:
                    stats['invalid'] += 1
                    if remove_invalid:
                        continue
                
                # Check empty
                if not example['input'].strip() or not example['output'].strip():
                    stats['empty'] += 1
                    if remove_empty:
                        continue
                
                # Check length
                if len(example['input']) < min_input_length or len(example['output']) < min_output_length:
                    stats['too_short'] += 1
                    continue
                
                # Check duplicates
                content_hash = self._hash_example(example)
                if content_hash in seen_hashes:
                    stats['duplicates'] += 1
                    if remove_duplicates:
                        continue
                
                seen_hashes.add(content_hash)
                
                # Normalize fields
                example['input'] = example['input'].strip()
                example['output'] = example['output'].strip()
                example.setdefault('intent_label', 0)
                example.setdefault('tone_label', 0)
                example.setdefault('metadata', {})
                
                examples.append(example)
                stats['kept'] += 1
        
        # Write cleaned dataset
        output_path = Path(output_path) if output_path else self.dataset_path
        
        with open(output_path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')
        
        print(f"Cleaning complete:")
        print(f"  Total: {stats['total']}")
        print(f"  Kept: {stats['kept']}")
        print(f"  Removed: {stats['total'] - stats['kept']}")
        print(f"    - Duplicates: {stats['duplicates']}")
        print(f"    - Empty: {stats['empty']}")
        print(f"    - Invalid: {stats['invalid']}")
        print(f"    - Too short: {stats['too_short']}")
        
        return stats
    
    def _hash_example(self, example: Dict) -> str:
        """Create hash of example content."""
        content = f"{example['input']}|{example['output']}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def merge(self, other_datasets: List[str], output_path: str):
        """
        Merge multiple JSONL files.
        
        Args:
            other_datasets: List of paths to other datasets
            output_path: Output merged dataset path
        """
        print(f"Merging {len(other_datasets) + 1} datasets...")
        
        all_examples = []
        
        # Read current dataset
        if self.dataset_path.exists():
            all_examples.extend(self._read_dataset(str(self.dataset_path)))
        
        # Read other datasets
        for dataset_path in other_datasets:
            all_examples.extend(self._read_dataset(dataset_path))
        
        # Write merged dataset
        with open(output_path, 'w') as f:
            for example in all_examples:
                f.write(json.dumps(example) + '\n')
        
        print(f"Merged {len(all_examples)} examples to {output_path}")
    
    def _read_dataset(self, path: str) -> List[Dict]:
        """Read all examples from a dataset file."""
        examples = []
        
        with open(path, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        example = json.loads(line)
                        examples.append(example)
                    except json.JSONDecodeError:
                        continue
        
        return examples
    
    def export_training_ready(self, output_path: str, 
                              train_split: float = 0.8,
                              val_split: float = 0.1,
                              test_split: float = 0.1,
                              shuffle: bool = True):
        """
        Export dataset split into train/val/test sets.
        
        Args:
            output_path: Base output path (will create train.jsonl, val.jsonl, test.jsonl)
            train_split: Training set ratio
            val_split: Validation set ratio
            test_split: Test set ratio
            shuffle: Shuffle dataset before splitting
        """
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Read all examples
        examples = self._read_dataset(str(self.dataset_path))
        
        print(f"Exporting {len(examples)} examples...")
        
        # Shuffle if requested
        if shuffle:
            import random
            random.shuffle(examples)
        
        # Calculate split sizes
        total = len(examples)
        train_size = int(total * train_split)
        val_size = int(total * val_split)
        
        train_examples = examples[:train_size]
        val_examples = examples[train_size:train_size + val_size]
        test_examples = examples[train_size + val_size:]
        
        # Write splits
        base_name = Path(output_path).stem
        
        train_path = output_dir / f"{base_name}_train.jsonl"
        val_path = output_dir / f"{base_name}_val.jsonl"
        test_path = output_dir / f"{base_name}_test.jsonl"
        
        self._write_examples(train_path, train_examples)
        self._write_examples(val_path, val_examples)
        self._write_examples(test_path, test_examples)
        
        print(f"Export complete:")
        print(f"  Train: {len(train_examples)} examples -> {train_path}")
        print(f"  Val: {len(val_examples)} examples -> {val_path}")
        print(f"  Test: {len(test_examples)} examples -> {test_path}")
    
    def _write_examples(self, path: Path, examples: List[Dict]):
        """Write examples to file."""
        with open(path, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')
    
    def get_statistics(self) -> Dict:
        """Get dataset statistics."""
        examples = self._read_dataset(str(self.dataset_path))
        
        intent_counts = Counter(ex.get('intent_label', 0) for ex in examples)
        tone_counts = Counter(ex.get('tone_label', 0) for ex in examples)
        
        input_lengths = [len(ex['input']) for ex in examples]
        output_lengths = [len(ex['output']) for ex in examples]
        
        stats = {
            'total_examples': len(examples),
            'intent_distribution': dict(intent_counts),
            'tone_distribution': dict(tone_counts),
            'avg_input_length': sum(input_lengths) / len(input_lengths) if input_lengths else 0,
            'avg_output_length': sum(output_lengths) / len(output_lengths) if output_lengths else 0,
            'max_input_length': max(input_lengths) if input_lengths else 0,
            'max_output_length': max(output_lengths) if output_lengths else 0
        }
        
        return stats
    
    def create_version(self, version_name: Optional[str] = None):
        """
        Create a versioned backup of the dataset.
        
        Args:
            version_name: Version name (default: timestamp)
        """
        if version_name is None:
            version_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        version_dir = self.dataset_dir / "versions"
        version_dir.mkdir(exist_ok=True)
        
        version_path = version_dir / f"{self.dataset_path.stem}_v{version_name}.jsonl"
        
        shutil.copy2(self.dataset_path, version_path)
        
        print(f"Created version: {version_path}")
        
        return str(version_path)


def cli():
    """Command-line interface for dataset tools."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SILS Dataset Tools")
    parser.add_argument("--dataset", type=str, required=True, help="Path to dataset")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Clean dataset")
    clean_parser.add_argument("--output", type=str, help="Output path")
    clean_parser.add_argument("--keep-duplicates", action="store_true", help="Keep duplicates")
    
    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge datasets")
    merge_parser.add_argument("--others", nargs="+", required=True, help="Other datasets to merge")
    merge_parser.add_argument("--output", type=str, required=True, help="Output path")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export train/val/test splits")
    export_parser.add_argument("--output", type=str, required=True, help="Output base path")
    export_parser.add_argument("--train-split", type=float, default=0.8, help="Train split")
    export_parser.add_argument("--val-split", type=float, default=0.1, help="Val split")
    
    # Stats command
    subparsers.add_parser("stats", help="Show dataset statistics")
    
    # Version command
    version_parser = subparsers.add_parser("version", help="Create dataset version")
    version_parser.add_argument("--name", type=str, help="Version name")
    
    args = parser.parse_args()
    
    # Create manager
    manager = DatasetManager(args.dataset)
    
    # Execute command
    if args.command == "clean":
        manager.clean(
            output_path=args.output,
            remove_duplicates=not args.keep_duplicates
        )
    
    elif args.command == "merge":
        manager.merge(args.others, args.output)
    
    elif args.command == "export":
        manager.export_training_ready(
            args.output,
            train_split=args.train_split,
            val_split=args.val_split
        )
    
    elif args.command == "stats":
        stats = manager.get_statistics()
        print(json.dumps(stats, indent=2))
    
    elif args.command == "version":
        manager.create_version(args.name)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    cli()
