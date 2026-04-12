import app

app.init_db()
client = app.app.test_client()
sess = client.session_transaction()
sess.__enter__()
sess['user'] = 'tester'
sess['user_id'] = 1
sess.__exit__(None, None, None)
response = client.get('/shipments')
print('status', response.status_code)
print(response.data.decode('utf-8')[:800])
