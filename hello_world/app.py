import boto3, os, logging
from aws_lambda_powertools.event_handler import (
  APIGatewayRestResolver,
)
from aws_lambda_powertools.event_handler.exceptions import (
  BadRequestError,
  NotFoundError,
)

app = APIGatewayRestResolver()

logger=logging.getLogger()
logger.setLevel(logging.INFO)

dynamo_db = boto3.client('dynamodb')
dynamo=boto3.resource('dynamodb')
product_table = dynamo.Table('products')

cors=True

@app.get("/products",cors=cors)
def get_all_products():
  try:
    payload = product_table.scan()
    
    if payload.get("Items"):
      result = payload["Items"]
      while 'LastEvaluatedKey' in payload:
        payload = product_table.scan(ExclusiveStarKey=payload["LastEvaluatedKey"])
        result.extend(payload["Items"])
      
      return result
    else:
      raise NotFoundError("No hay productos en la base de datos.")
      
    
  except Exception as e:
    raise BadRequestError(str(e))

@app.post("/product",cors=cors)
def create_product():
  request_body = app.current_event.json_body
  logger.info(request_body)
  try:
    product_table.put_item(Item=request_body)
    return request_body
  except dynamo_db.exceptions.ConditionalCheckFailedException:
    raise BadRequestError("El item ya existe")

@app.get("/product/<product>",cors=cors)
def read_product(product: str):
  try:
    response = product_table.get_item(
      Key={'product':product}
    )
    logger.info(response)
    if response.get("Item"):
      return response["Item"]
    else:
      raise NotFoundError("Producto no encontrado")
  except Exception as e:
    raise BadRequestError(str(e))

@app.patch("/product",cors=cors)
def modify_product():
  payload = app.current_event.json_body
  try:
    response_body = product_table.update_item(
      Key={'product': payload["product"]},
      UpdateExpression="SET %s = :value" % payload["key"],
      ExpressionAttributeValues={":value": payload["value"]},
      ReturnValues="UPDATED_NEW"
    )
    
    if response_body.get("Attributes"):
      return response_body["Attributes"]
    else:
      raise NotFoundError("No encontrado")
  except Exception as e:
    raise BadRequestError(str(e))

@app.put("/product/<product>",cors=cors)
def update_product(product: str):
  payload = app.current_event.json_body
  try:
    response = product_table.update_item(
      Key={"product": product},
      UpdateExpression="SET #na = :n, #pr = :p",
      ExpressionAttributeValues={
        ":n": payload["name"],
        ":p": payload["price"]
      },
      ExpressionAttributeNames={
        "#na": "name",
        "#pr": "price"
      },
      ReturnValues="UPDATED_NEW"
    )
    if response.get("Attributes"):
      return response["Attributes"]
    else:
      raise NotFoundError("No encontrado")
  except Exception as e:
    raise BadRequestError(str(e))

@app.delete("/product/<product>",cors=cors)
def delete_product(product: str):
  response_body = product_table.delete_item(
    Key={'product':product},
    ReturnValues="ALL_OLD"
  )
  
  if response_body.get("Attributes"):
    return response_body["Attributes"]
  else:
    raise NotFoundError("No encontrado")

def lambda_handler(event, context):
  return app.resolve(event, context)