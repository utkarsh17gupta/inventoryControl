from flask import Flask, request, jsonify
from simple_salesforce import Salesforce
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

sf = Salesforce(
    username=os.getenv('SF_USERNAME'),
    password=os.getenv('SF_PASSWORD'),
    security_token=os.getenv('SF_SECURITY_TOKEN'),
    domain='login'
)

def get_ids(sku, warehouse_name):
    product = sf.query(f"SELECT Id FROM Product__c WHERE SKU__c = '{sku}'")
    warehouse = sf.query(f"SELECT Id FROM Warehouse__c WHERE Name = '{warehouse_name}'")
    if not product['records'] or not warehouse['records']:
        return None, None
    return product['records'][0]['Id'], warehouse['records'][0]['Id']

def update_quantity(product_id, warehouse_id, delta):
    inventory = sf.query(
        f"SELECT Id, Quantity__c FROM Inventory__c "
        f"WHERE Product__c = '{product_id}' AND Warehouse__c = '{warehouse_id}'"
    )
    if inventory['records']:
        record = inventory['records'][0]
        new_quantity = max(0, record['Quantity__c'] + delta)
        sf.Inventory__c.update(record['Id'], {'Quantity__c': new_quantity})
    elif delta > 0:
        sf.Inventory__c.create({
            'Product__c': product_id,
            'Warehouse__c': warehouse_id,
            'Quantity__c': delta
        })

@app.route('/inventory/update', methods=['POST'])
def inventory_update():
    payload = request.get_json()

    for item in payload.get('add', []):
        product_id, warehouse_id = get_ids(item['sku'], item['warehouse_name'])
        if product_id and warehouse_id:
            update_quantity(product_id, warehouse_id, item['quantity'])

    for item in payload.get('remove', []):
        product_id, warehouse_id = get_ids(item['sku'], item['warehouse_name'])
        if product_id and warehouse_id:
            update_quantity(product_id, warehouse_id, -item['quantity'])

    return jsonify({'status': 'success'}), 200

if __name__ == '__main__':
    app.run()
