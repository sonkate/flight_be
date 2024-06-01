import hmac
import json
import hashlib
from pydantic import Field
from fastapi import APIRouter, Header, Depends, Body
from schemas.user import serializeDict, serializeList
from config.db import db
from bson import ObjectId
from provider.authProvider import get_userId_from_request
from provider.jwtProvider import jwtBearer
import datetime
import base64
from decouple import config
import aiohttp
from models.CustomBaseModels import CustomBaseModel

from routes.voucher import get_voucher_detail

import secrets
SECRET_KEY = 'secret_key123'
BLOCKCHAIN_BASE_URL = "https://on-shop-blockchain.onrender.com"
API_KEY = 'enBWafDO3SxLlfK90fGWSxRSGESGrBkrloCuRCu6K6Q'
PARTNER_CODE = '5c36210ae5b06ad5c7b387931582feef'
cart = APIRouter()


def create_signature(body, api_key):
    message = json.dumps(body) + api_key
    signature = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return signature

@cart.get('', dependencies=[Depends(jwtBearer())])
async def get_all_cart_items(Authorization: str = Header(default=None)):
    try:
        userId = get_userId_from_request(Authorization)
        cartList = serializeList(db.cart.aggregate([
            {
                '$lookup': {
                    'from': 'tickets',
                    'localField': 'ticketId',
                    'foreignField': '_id',
                    'as': 'items'
                }
            }, {
                '$lookup': {
                    'from': 'user',
                    'localField': 'userId',
                    'foreignField': '_id',
                    'as': 'users'
                }
            }
        ]))

        myCartList = []
        for cart in cartList:
            if str(cart['userId']) == str(userId):
                for item in cart['items']:
                    item['id'] = str(item['_id'])
                    item.pop('_id')
                    myCartList.append(item)

        return {'success': True, 'data': myCartList}
    except:
        return {'success': False}


@cart.get('/{id}', dependencies=[Depends(jwtBearer())])
async def get_cart_item(id: str):
    cartItem = serializeList(db.cart.aggregate([
        {
            '$match': {
                '_id': ObjectId(id),
            }
        },
        {
            '$sort': {
                'created_at': -1
            }
        },
        {
            '$lookup': {
                'from': 'voucher',
                'localField': 'ticketId',
                'foreignField': '_id',
                'as': 'items'
            }
        }
    ]))

    currentCartItem = cartItem[0]['items'][0]
    currentCartItem['id'] = str(currentCartItem['_id'])
    currentCartItem.pop('_id')

    return currentCartItem


@cart.post('', dependencies=[Depends(jwtBearer())])
async def add_cart_item(ticketId: str, Authorization: str = Header(default=None)):
    try:
        userId = get_userId_from_request(Authorization)
        id = ObjectId()

        ticket = {
            '_id': id,
            'userId': userId,
            'ticketId': ObjectId(ticketId),
            'created_at': datetime.datetime.now(),
        }
        print(ticket)

        db.cart.insert_one(dict(ticket))
        cartItem = await get_cart_item(str(id))

        return {'success': True, 'message': 'add ticket successfully', 'data': cartItem}
    except:
        return {'success': False}


@cart.delete('/{id}')
async def delete_cart(id):
    return serializeDict(db.cart.find_one_and_delete({'_id': ObjectId(id)}))


@cart.post('/paypal/create-order', dependencies=[Depends(jwtBearer())])
async def createBlockChainOrder(order: object = Body(default=None)):
    if order is None:
        print('order is none')
    print('order: ',order)
    ticketId = order['ticketId']
    voucher_detail = await get_voucher_detail(ticketId)
    print('voucher_detail: ',voucher_detail)
    # call api
    data = {
        'order_name': voucher_detail['brand'],
        'amount': voucher_detail['salePrice'],
        'currency': 'USDT',
        'image': voucher_detail['image'],
        'order_id': secrets.token_hex(12)
    }
    sign = create_signature(data, API_KEY)
    headers = {
        'merchant': PARTNER_CODE,
        'sign': sign,
        'api_key': API_KEY
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f'{BLOCKCHAIN_BASE_URL}/get_order_input', json=data, headers=headers, timeout=60) as response:
                # Check if the request was successful
                if response.status == 200:
                    text = await response.json()
                    # payment_link = request.url_for("payment_page", amount=amount, _external=True)
                    return text
                elif response.status == 400:
                    error_message = await response.text()
                    print(f"Error: Received status code 400 with message: {error_message}")
                else:
                    # Handle other unsuccessful response codes
                    print(f"Error: Received status code {response.status}")
                    return None
    except Exception as e:
        # Handle exceptions that may occur during the request
        print(f"Error: {str(e)}")
        return None
    


# @cart.post('/paypal/approve-order', dependencies=[Depends(jwtBearer())])
# async def createPaypalOrder(data: PaypalApprove):
#     try:
#         accessToken = await generate_access_token()
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {accessToken}",
#         }

#         async with httpx.AsyncClient(base_url=PAYPAL_BASE_URL, headers=headers) as client:
#             response = await client.post(f"/v2/checkout/orders/{data.orderId}/capture")

#             return response.json()
#     except:
#         return {'success': False}
