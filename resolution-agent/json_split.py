import json

def split_json_by_user_requests(input_data):
    """
    Split JSON data so that each user request becomes a separate JSON object.
    
    Args:
        input_data: List of dictionaries containing the original JSON data
    
    Returns:
        List of dictionaries where each contains only one user request
    """
    result = []
    
    for item in input_data:
        # Find all user request keys in the current item
        user_request_keys = [key for key in item.keys() if key.startswith('user_request_')]
        
        # Create a separate JSON object for each user request
        for request_key in user_request_keys:
            # Create a new dictionary with all original fields except other user requests
            new_item = {}
            
            # Copy all non-user-request fields
            for key, value in item.items():
                if not key.startswith('user_request_'):
                    new_item[key] = value
            
            # Add only the current user request
            new_item['user_request'] = item[request_key]
            
            result.append(new_item)
    
    return result

# Read the input JSON (assuming it's in a file called 'input.json')
def process_json_file(input_file_path, output_file_path):
    """
    Process JSON file and save the split result to output file.
    
    Args:
        input_file_path: Path to input JSON file
        output_file_path: Path to output JSON file
    """
    # Read input JSON
    with open(input_file_path, 'r') as file:
        input_data = json.load(file)
    
    # Split the JSON
    split_data = split_json_by_user_requests(input_data)
    
    # Write output JSON
    with open(output_file_path, 'w') as file:
        json.dump(split_data, file, indent=2)
    
    print(f"Successfully split {len(input_data)} records into {len(split_data)} records")
    print(f"Output saved to {output_file_path}")

# Example usage:
if __name__ == "__main__":
    # Your original JSON data
    # original_data = 
    
    # Process the data
    # split_result = process_json_data(original_data)
    
    # Print results
    # print("Split JSON data:")
    # for i, item in enumerate(split_result[:3]):  # Show first 3 items as example
    #     print(f"\nRecord {i+1}:")
    #     print(json.dumps(item, indent=2))
    
    # Or save to files
    process_json_file('data/transcripts_policies.json', 'data/transcripts_policies_output.json')