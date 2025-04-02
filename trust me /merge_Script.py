import json
import os
import ijson  # You might need to install this: pip install ijson

def process_large_json_file(filename, label_filter):
    """Process a large JSON file and yield items matching the label filter."""
    items = []
    
    # Check file size
    file_size = os.path.getsize(filename)
    large_file = file_size > 100 * 1024 * 1024  # 100MB threshold
    
    with open(filename, 'r', encoding='utf-8') as f:
        if large_file:
            # For very large files, use ijson to stream the parsing
            try:
                # Try parsing as an array of objects
                for item in ijson.items(f, 'item'):
                    if "label" in item and item["label"] == label_filter:
                        items.append(item)
                        # If memory is a concern, yield instead of storing
                        if len(items) >= 1000:  # Process in batches of 1000
                            for item_to_yield in items:
                                yield item_to_yield
                            items = []  # Clear the batch
            except ijson.JSONError:
                # If not an array, try parsing as one object per line (JSON Lines)
                f.seek(0)
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if "label" in item and item["label"] == label_filter:
                                yield item
                        except json.JSONDecodeError:
                            print(f"Error parsing line in {filename}: {line[:50]}...")
        else:
            # For smaller files, regular json.load is fine
            try:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if "label" in item and item["label"] == label_filter:
                            items.append(item)
                elif isinstance(data, dict) and "label" in data and data["label"] == label_filter:
                    items.append(data)
            except json.JSONDecodeError:
                # Try JSON Lines format
                f.seek(0)
                for line in f:
                    if line.strip():
                        try:
                            item = json.loads(line)
                            if "label" in item and item["label"] == label_filter:
                                items.append(item)
                        except json.JSONDecodeError:
                            print(f"Error parsing line in {filename}: {line[:50]}...")
    
    # Yield any remaining items
    for item in items:
        yield item

def merge_json_files(file1, file2, output_file, label1="1", label2="0"):
    """Merge two JSON files by alternating items with specified labels."""
    # Create iterators
    items1 = process_large_json_file(file1, label1)
    items2 = process_large_json_file(file2, label2)
    
    # We'll use a streaming approach for writing too
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write("[\n")
        
        # Try to get first items
        try:
            item1 = next(items1, None)
            item2 = next(items2, None)
            
            first_item = True
            count = 0
            
            while item1 is not None or item2 is not None:
                # Write item2 (label "0") first
                if item2 is not None:
                    if not first_item:
                        out.write(",\n")
                    else:
                        first_item = False
                    
                    json.dump(item2, out, ensure_ascii=False, indent=2)
                    count += 1
                    item2 = next(items2, None)
                
                # Write item1 (label "1")
                if item1 is not None:
                    if not first_item:
                        out.write(",\n")
                    else:
                        first_item = False
                    
                    json.dump(item1, out, ensure_ascii=False, indent=2)
                    count += 1
                    item1 = next(items1, None)
                
                # Flush periodically to avoid buffer buildup
                if count % 100 == 0:
                    out.flush()
            
        except StopIteration:
            pass
        
        out.write("\n]")
    
    print(f"Successfully merged items into {output_file}")

if __name__ == "__main__":
    # File paths - adjust as needed
    file1 = "JAILBREAK.json"      # File with label "1" items
    file2 = "NOBREAK.json"    # File with label "0" items
    output_file = "merged_responses.json"
    
    merge_json_files(file1, file2, output_file)