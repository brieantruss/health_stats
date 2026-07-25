import time
import os
from google.cloud import bigquery

def deploy():
    # Service account key path on the VM
    key_path = '/home/briean/.gcp/bigquery-agent-key.json'
    view_id = 'my-data-479716.health_stats.view_weather_aqi'
    query_file = '/tmp/query_aqi.sql'
    success_file = '/tmp/deploy_success_aqi.txt'
    
    if os.path.exists(success_file):
        os.remove(success_file)
        
    for i in range(20):
        try:
            print(f"Attempt {i+1} to deploy view...")
            client = bigquery.Client.from_service_account_json(key_path)
            
            with open(query_file, 'r') as f:
                query_sql = f.read()
                
            view = bigquery.Table(view_id)
            view.view_query = query_sql
            
            client.delete_table(view_id, not_found_ok=True)
            client.create_table(view)
            
            # Verify existence
            client.get_table(view_id)
            
            with open(success_file, 'w') as f:
                f.write("SUCCESS")
                
            print("View deployed and verified successfully!")
            return
        except Exception as e:
            print(f"Attempt {i+1} failed with error: {e}")
            time.sleep(3)
            
    print("All attempts failed.")

if __name__ == '__main__':
    deploy()
