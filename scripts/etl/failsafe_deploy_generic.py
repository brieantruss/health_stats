import sys
import time
import os
from google.cloud import bigquery

def deploy():
    if len(sys.argv) < 4:
        print("Usage: failsafe_deploy_generic.py <view_id> <query_file> <success_file>")
        return
        
    view_id = sys.argv[1]
    query_file = sys.argv[2]
    success_file = sys.argv[3]
    key_path = '/home/briean/.gcp/bigquery-agent-key.json'
    
    if os.path.exists(success_file):
        os.remove(success_file)
        
    for i in range(20):
        try:
            print(f"Attempt {i+1} to deploy view {view_id}...")
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
                
            print(f"View {view_id} deployed and verified successfully!")
            return
        except Exception as e:
            print(f"Attempt {i+1} failed with error: {e}")
            time.sleep(3)
            
    print("All attempts failed.")

if __name__ == '__main__':
    deploy()
