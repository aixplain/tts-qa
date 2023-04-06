import ast
import csv

with open('./anotations.txt', 'r', encoding='utf8') as f:
    content = ast.literal_eval(f.read())

    # Extract all unique values from the 'Problems' column
    unique_problems = set()
    for d in content:
        unique_problems.update(d['Problems'])

    # Create new column names based on unique values
    new_columns = list(unique_problems)

    # Modify the list of dictionaries to replace 'Problems' column with new columns
    for d in content:
        tags = d.pop('Problems')
        for column in new_columns:
            d[column] = 'yes' if column in tags else 'no'
 
with open('anotations.csv', 'w', encoding='utf8') as f:
    fieldnames=content[0].keys()
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    
    # Write the column headers
    writer.writeheader()

    # Write the data for each dictionary
    writer.writerows(content)
