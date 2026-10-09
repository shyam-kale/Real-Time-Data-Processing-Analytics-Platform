import requests

headers = {"X-API-Key": "df_ygrUvTYaE3dIiv3wnZprel8b4sxubaiQTqA9XiQXqOw"}
base = "https://real-time-data-processing-analytics-platform-production-8c61.up.railway.app/api/v1"

# Get datasets
datasets = requests.get(f"{base}/orgs/org-1/datasets", headers=headers).json()
print(datasets)
