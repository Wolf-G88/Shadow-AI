"""
Complete Tokenizer for SILS v1
WordPiece with dynamic vocab and special tokens
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import Counter, defaultdict
import re


class ShadowTokenizer:
    """
    Full WordPiece tokenizer with dynamic vocabulary.
    
    Special tokens: <PAD>, <UNK>, <BOS>, <EOS>, <STYLE>, <INTENT>
    """
    
    def __init__(self, vocab: Optional[Dict[str, int]] = None, merges: Optional[List[Tuple[str, str]]] = None):
        # Special tokens (fixed IDs)
        self.special_tokens = ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<STYLE>", "<INTENT>"]
        
        self.pad_token = "<PAD>"
        self.unk_token = "<UNK>"
        self.bos_token = "<BOS>"
        self.eos_token = "<EOS>"
        self.style_token = "<STYLE>"
        self.intent_token = "<INTENT>"
        
        self.pad_id = 0
        self.unk_id = 1
        self.bos_id = 2
        self.eos_id = 3
        self.style_id = 4
        self.intent_id = 5
        
        # Initialize vocabulary
        if vocab is None:
            self.token_to_id = {token: i for i, token in enumerate(self.special_tokens)}
            self.id_to_token = {i: token for token, i in self.token_to_id.items()}
        else:
            self.token_to_id = vocab
            self.id_to_token = {v: k for k, v in vocab.items()}
        
        # BPE merges for WordPiece
        self.merges = merges or []
        self.merge_ranks = {merge: i for i, merge in enumerate(self.merges)}
        
        self.vocab_size = len(self.token_to_id)
    
    def train(self, texts: List[str], vocab_size: int = None, min_frequency: int = 2):
        """
        Train WordPiece vocabulary using BPE algorithm.
        
        Args:
            texts: Training texts
            vocab_size: Target vocabulary size
            min_frequency: Minimum frequency for subword
        """
        print(f"Training tokenizer on {len(texts)} texts...")
        
        # If no vocab_size specified, calculate from data
        if vocab_size is None:
            # Count unique words as estimate
            unique_tokens = set()
            for text in texts:
                unique_tokens.update(text.lower().split())
            vocab_size = len(unique_tokens) * 2  # 2x for subwords
            print(f"Auto-calculated vocab_size: {vocab_size}")
        
        # Initialize with special tokens
        vocab = {token: i for i, token in enumerate(self.special_tokens)}
        next_id = len(vocab)
        
        # Step 1: Character-level base vocabulary
        char_freq = Counter()
        for text in texts:
            text = text.lower().strip()
            for char in text:
                if not char.isspace():
                    char_freq[char] += 1
        
        # Add frequent characters to vocab
        for char, freq in char_freq.most_common():
            if freq >= min_frequency and char not in vocab:
                vocab[char] = next_id
                next_id += 1
                if len(vocab) >= vocab_size // 2:
                    break
        
        print(f"Base vocabulary: {len(vocab)} tokens (chars + special)")
        
        # Step 2: Build word frequency dictionary
        word_splits = defaultdict(int)
        for text in texts:
            words = self._pre_tokenize(text)
            for word in words:
                word_chars = tuple(list(word) + ['</w>'])
                word_splits[word_chars] += 1
        
        print(f"Word splits: {len(word_splits)} unique words")
        
        # Step 3: Iteratively merge most frequent pairs (BPE)
        merges = []
        
        while len(vocab) < vocab_size:
            # Count pair frequencies
            pair_freq = defaultdict(int)
            
            for word_tuple, freq in word_splits.items():
                for i in range(len(word_tuple) - 1):
                    pair = (word_tuple[i], word_tuple[i + 1])
                    pair_freq[pair] += freq
            
            if not pair_freq:
                break
            
            # Find most frequent pair
            best_pair = max(pair_freq.items(), key=lambda x: x[1])[0]
            
            # Create merged token
            merged_token = ''.join(best_pair)
            
            if merged_token in vocab:
                word_splits = self._merge_pair(word_splits, best_pair)
                continue
            
            # Add to vocabulary
            vocab[merged_token] = next_id
            next_id += 1
            merges.append(best_pair)
            
            # Update word splits with new merge
            word_splits = self._merge_pair(word_splits, best_pair)
            
            if len(vocab) % 500 == 0:
                print(f"Vocabulary size: {len(vocab)}")

        # Step 4: If BPE merges saturate early, add whole-word tokens for
        # frequent remaining words so larger-vocab experiments are real.
        if len(vocab) < vocab_size:
            whole_word_freq = Counter()
            for text in texts:
                for word in self._pre_tokenize(text):
                    if word:
                        whole_word_freq[f"{word}</w>"] += 1

            for token, freq in whole_word_freq.most_common():
                if len(vocab) >= vocab_size:
                    break
                if freq < min_frequency:
                    continue
                if token in vocab:
                    continue
                vocab[token] = next_id
                next_id += 1
        
        self.token_to_id = vocab
        self.id_to_token = {v: k for k, v in vocab.items()}
        self.merges = merges
        self.merge_ranks = {merge: i for i, merge in enumerate(merges)}
        self.vocab_size = len(vocab)
        
        print(f"Training complete! Final vocab size: {self.vocab_size}")
    
    def _pre_tokenize(self, text: str) -> List[str]:
        """Split text into words."""
        text = text.lower().strip()
        words = re.findall(r'\w+|[^\w\s]', text)
        return [w for w in words if w]
    
    def _merge_pair(self, word_splits: Dict[Tuple, int], pair: Tuple[str, str]) -> Dict[Tuple, int]:
        """Merge a pair in all word splits."""
        new_splits = defaultdict(int)
        
        for word_tuple, freq in word_splits.items():
            new_word = []
            i = 0
            while i < len(word_tuple):
                if i < len(word_tuple) - 1 and (word_tuple[i], word_tuple[i + 1]) == pair:
                    new_word.append(''.join(pair))
                    i += 2
                else:
                    new_word.append(word_tuple[i])
                    i += 1
            
            new_splits[tuple(new_word)] += freq
        
        return new_splits
    
    def encode(self, text: str, max_length: int = None, add_special_tokens: bool = True, 
               add_style: bool = False, add_intent: bool = False, pad: bool = False) -> List[int]:
        """
        Encode text to token IDs.
        
        Args:
            text: Input text
            max_length: Maximum sequence length (None = no limit)
            add_special_tokens: Add BOS/EOS
            add_style: Add STYLE marker
            add_intent: Add INTENT marker
            pad: Whether to pad to max_length (only for training batches)
        
        Returns:
            List of token IDs
        """
        tokens = self._tokenize(text)
        
        token_ids = []
        
        if add_special_tokens:
            token_ids.append(self.bos_id)
        
        if add_style:
            token_ids.append(self.style_id)
        
        if add_intent:
            token_ids.append(self.intent_id)
        
        for token in tokens:
            token_id = self.token_to_id.get(token, self.unk_id)
            token_ids.append(token_id)
        
        if add_special_tokens:
            token_ids.append(self.eos_id)
        
        # Truncate or pad only if max_length specified
        if max_length is not None:
            if len(token_ids) > max_length:
                token_ids = token_ids[:max_length]
                if add_special_tokens:
                    token_ids[-1] = self.eos_id
            elif pad:
                # Only pad if explicitly requested (training only)
                token_ids.extend([self.pad_id] * (max_length - len(token_ids)))
        
        return token_ids
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text using learned BPE merges."""
        words = self._pre_tokenize(text)
        
        tokens = []
        for word in words:
            whole_word_token = f"{word}</w>"
            if whole_word_token in self.token_to_id:
                tokens.append(whole_word_token)
                continue

            word_tokens = list(word) + ['</w>']
            
            while len(word_tokens) > 1:
                pairs = [(i, (word_tokens[i], word_tokens[i + 1])) 
                        for i in range(len(word_tokens) - 1)]
                
                valid_pairs = [(i, pair) for i, pair in pairs if pair in self.merge_ranks]
                
                if not valid_pairs:
                    break
                
                merge_pos, merge_pair = min(valid_pairs, key=lambda x: self.merge_ranks[x[1]])
                
                new_tokens = []
                i = 0
                while i < len(word_tokens):
                    if i == merge_pos:
                        new_tokens.append(''.join(merge_pair))
                        i += 2
                    else:
                        new_tokens.append(word_tokens[i])
                        i += 1
                
                word_tokens = new_tokens
            
            tokens.extend(word_tokens)
        
        return tokens
    
    def decode(self, token_ids: List[int], skip_special_tokens: bool = True) -> str:
        """Decode token IDs to text."""
        tokens = []
        
        for token_id in token_ids:
            if token_id == self.pad_id:
                continue
            
            if skip_special_tokens and token_id in [self.bos_id, self.eos_id, self.style_id, self.intent_id]:
                continue
            
            token = self.id_to_token.get(token_id, self.unk_token)
            tokens.append(token)
        
        text = ''.join(tokens)
        text = text.replace('</w>', ' ')
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def batch_encode(self, texts: List[str], max_length: int = 192, **kwargs) -> List[List[int]]:
        """Batch encode multiple texts."""
        return [self.encode(text, max_length, **kwargs) for text in texts]
    
    def batch_decode(self, batch_ids: List[List[int]], **kwargs) -> List[str]:
        """Batch decode multiple sequences."""
        return [self.decode(ids, **kwargs) for ids in batch_ids]
    
    def save(self, path: str):
        """Save tokenizer metadata to JSON."""
        metadata = {
            'vocab': self.token_to_id,
            'merges': self.merges,
            'special_tokens': self.special_tokens,
            'vocab_size': self.vocab_size
        }
        
        with open(path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Tokenizer saved to {path}")
    
    @classmethod
    def load(cls, path: str):
        """Load tokenizer from JSON."""
        with open(path, 'r') as f:
            metadata = json.load(f)
        
        # Handle both 'vocab' and 'token_to_id' formats
        vocab = metadata.get('vocab', metadata.get('token_to_id', {}))
        merges = metadata.get('merges', [])
        
        tokenizer = cls(
            vocab=vocab,
            merges=[tuple(m) for m in merges] if merges else []
        )
        
        print(f"Tokenizer loaded from {path}")
        return tokenizer
    
    def get_vocab(self) -> Dict[str, int]:
        """Get vocabulary dictionary."""
        return self.token_to_id.copy()
    
    def get_vocab_size(self) -> int:
        """Get vocabulary size."""
        return self.vocab_size
    
    def extend_vocab(self, new_tokens: List[str]):
        """Extend vocabulary with new tokens."""
        next_id = max(self.token_to_id.values()) + 1
        
        for token in new_tokens:
            if token not in self.token_to_id:
                self.token_to_id[token] = next_id
                self.id_to_token[next_id] = token
                next_id += 1
        
        self.vocab_size = len(self.token_to_id)
        print(f"Extended vocab to {self.vocab_size} tokens")


def _load_text_lines(path: Path) -> List[str]:
    """Load plain-text lines from txt/md/log/jsonl-style corpus files."""
    if not path.exists():
        return []

    suffix = path.suffix.lower()
    texts: List[str] = []

    with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
        if suffix == '.jsonl':
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    record = json.loads(raw_line)
                except json.JSONDecodeError:
                    texts.append(raw_line)
                    continue

                if isinstance(record, dict):
                    for key in ('text', 'input', 'output', 'cleaned', 'content'):
                        value = record.get(key)
                        if isinstance(value, str) and value.strip():
                            texts.append(value.strip())
                elif isinstance(record, str) and record.strip():
                    texts.append(record.strip())
        else:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if raw_line:
                    texts.append(raw_line)

    return texts


def _load_seed_tokens(path: Path) -> List[str]:
    """Load seed tokens from txt/json/jsonl files."""
    if not path.exists():
        return []

    suffix = path.suffix.lower()
    tokens: List[str] = []

    with open(path, 'r', encoding='utf-8', errors='ignore') as handle:
        if suffix == '.json':
            payload = json.load(handle)
            if isinstance(payload, list):
                for item in payload:
                    if isinstance(item, str) and item.strip():
                        tokens.append(item.strip().lower())
            elif isinstance(payload, dict):
                values = payload.get('tokens') or payload.get('words') or []
                for item in values:
                    if isinstance(item, str) and item.strip():
                        tokens.append(item.strip().lower())
        else:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                if suffix == '.jsonl':
                    try:
                        record = json.loads(raw_line)
                    except json.JSONDecodeError:
                        tokens.append(raw_line.lower())
                        continue
                    if isinstance(record, str) and record.strip():
                        tokens.append(record.strip().lower())
                    elif isinstance(record, dict):
                        value = record.get('token') or record.get('word')
                        if isinstance(value, str) and value.strip():
                            tokens.append(value.strip().lower())
                else:
                    tokens.append(raw_line.lower())

    deduped: List[str] = []
    seen = set()
    for token in tokens:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def build_tokenizer_from_dataset(dataset_path: str, vocab_size: int = None,
                                 save_path: Optional[str] = None,
                                 min_frequency: int = 2,
                                 extra_text_paths: Optional[List[str]] = None,
                                 seed_tokens_path: Optional[str] = None) -> ShadowTokenizer:
    """Build tokenizer from training dataset."""
    texts = []
    
    with open(dataset_path, 'r') as f:
        for line in f:
            if line.strip():
                example = json.loads(line)
                texts.append(example.get('input', ''))
                texts.append(example.get('output', example.get('cleaned', '')))

    if extra_text_paths:
        for extra_path in extra_text_paths:
            if not extra_path:
                continue
            texts.extend(_load_text_lines(Path(extra_path)))
    
    print(f"Loaded {len(texts)} texts from {dataset_path}")
    
    tokenizer = ShadowTokenizer()
    tokenizer.train(texts, vocab_size=vocab_size, min_frequency=min_frequency)

    if seed_tokens_path:
        seed_tokens = _load_seed_tokens(Path(seed_tokens_path))
        if seed_tokens:
            tokenizer.extend_vocab([f"{token}</w>" for token in seed_tokens if token])
    
    if save_path:
        tokenizer.save(save_path)
    
    return tokenizer
