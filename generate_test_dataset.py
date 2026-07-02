import pandas as pd
import numpy as np

def create_demo_data():
    # Define columns with deliberately introduced data quality issues
    data = {
        'EmployeeID': [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 101], # Duplicate 101
        'Name': ['Alice Smith', 'Bob Jones', 'Charlie Brown', 'Diana Prince', 'Evan Wright', 'Fiona Gallagher', 'George Costanza', 'Helen Mirren', 'Ian McKellen', 'Julia Roberts', 'Alice Smith'], # Duplicate row
        'Age': [28, 34, np.nan, 45, 52, np.nan, 39, 41, 65, 31, 28], # Missing values
        'Gender': ['Female', 'Male', 'male', 'Female', 'M', 'Female', 'MALE', 'Female', 'Male', 'Female', 'Female'], # Format variations (Female, Male, male, M, MALE)
        'Salary': [55000, 62000, 75000, -8000, 92000, 48000, 120000, np.nan, 85000, 95000, 55000], # Unexpected negative salary (-8000), missing value
        'Department': ['HR', 'IT', 'IT', 'Marketing', 'Sales', 'HR', 'IT', 'Sales', 'Marketing', 'IT', 'HR'],
        'Notes': ['Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active', 'Active'] # Constant column (all "Active")
    }

    df = pd.DataFrame(data)
    
    # Save as CSV
    df.to_csv('demo_dataset.csv', index=False)
    print("demo_dataset.csv created successfully!")
    
    # Save as Excel
    df.to_excel('demo_dataset.xlsx', index=False)
    print("demo_dataset.xlsx created successfully!")

if __name__ == '__main__':
    create_demo_data()
