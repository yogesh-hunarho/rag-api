import json
import csv
import os

def json_to_csv(json_file_path, csv_file_path):
    # Check if JSON file exists
    if not os.path.exists(json_file_path):
        print(f"Error: {json_file_path} not found.")
        return

    try:
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not data or not isinstance(data, list):
            print("Error: JSON data is empty or not a list of objects.")
            return

        # Get headers from the first object
        headers = list(data[0].keys())

        # Write to CSV
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)

        print(f"Successfully converted {json_file_path} to {csv_file_path}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Define paths
    workspace_root = os.path.dirname(os.path.abspath(__file__))
    input_json = os.path.join(workspace_root, "text_output", "question_paper.json")
    output_csv = os.path.join(workspace_root, "question_paper.csv")

    json_to_csv(input_json, output_csv)
