import json
import csv
import os

def json_to_csv(input_file, output_file):
    """
    Convert a JSON file containing an array of objects to CSV format.
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str): Path to the output CSV file
    """
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return
    
    try:
        # Load the JSON data
        print(f"Reading JSON data from '{input_file}'...")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            print("Error: JSON data is not an array of objects.")
            return
        
        if len(data) == 0:
            print("Warning: JSON array is empty.")
            return
        
        # Determine CSV headers
        # Assuming all objects have the same structure as the first one
        sample_item = data[0]
        headers = list(sample_item.keys())
        
        print(f"Found {len(data)} items with columns: {', '.join(headers)}")
        
        # Write to CSV
        print(f"Writing data to '{output_file}'...")
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            # Process items in batches to handle large files
            batch_size = 1000
            total_written = 0
            
            for i in range(0, len(data), batch_size):
                batch = data[i:i+batch_size]
                for item in batch:
                    # Handle any missing keys by filling with empty strings
                    row = {header: item.get(header, '') for header in headers}
                    writer.writerow(row)
                
                total_written += len(batch)
                print(f"Progress: {total_written}/{len(data)} items written ({(total_written/len(data)*100):.1f}%)")
        
        print(f"Conversion complete! Data saved to '{output_file}'")
        
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    input_file = "merged_responses.json"
    output_file = "merged_responses.csv"
    
    json_to_csv(input_file, output_file)