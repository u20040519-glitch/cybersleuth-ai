import os
import re

test_dir = 'tests'
for fname in os.listdir(test_dir):
    if fname.endswith('.py'):
        fpath = os.path.join(test_dir, fname)
        with open(fpath, 'r') as f:
            content = f.read()
        
        # Replace import
        content = content.replace(
            'from httpx import AsyncClient',
            'from httpx import AsyncClient, ASGITransport'
        )
        # Replace AsyncClient(app=app, ...) usage
        content = content.replace(
            'AsyncClient(app=app, base_url="http://test")',
            'AsyncClient(transport=ASGITransport(app=app), base_url="http://test")'
        )
        
        with open(fpath, 'w') as f:
            f.write(content)
        
        print(f'Updated {fname}')
