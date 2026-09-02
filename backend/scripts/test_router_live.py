import urllib.request
import json
import time

def test_live():
    payload = json.dumps({'task_type': 'code_exec', 'input_ref': 'Calculate the sum of first 50 prime numbers'}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/tasks/', data=payload, headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req)
    task_id = json.loads(resp.read().decode('utf-8'))['id']
    print(f"Created task: {task_id}")

    for i in range(25):
        time.sleep(2)
        t_req = urllib.request.urlopen(f"http://127.0.0.1:8000/tasks/{task_id}")
        t_data = json.loads(t_req.read().decode('utf-8'))
        st = t_data.get('status')
        steps = t_data.get('steps', [])
        print(f"Poll {i+1}: status = {st}, steps count = {len(steps)}")
        if st in ['done', 'failed']:
            print("\n--- AGENT EXECUTION TRACE ---")
            for s in steps:
                print(f"Step {s.get('step_number')}: [{s.get('tool_called')}] {s.get('description')}")
            print("\n--- FINAL OUTPUT ---")
            print(t_data.get('output_ref'))
            break

if __name__ == '__main__':
    test_live()
