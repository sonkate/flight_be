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
import httpx
from models.CustomBaseModels import CustomBaseModel

import secrets
# PAYPAL_CLIENT_ID = config('PAYPAL_CLIENT_ID')
# PAYPAL_CLIENT_SECRET = config('PAYPAL_CLIENT_SECRET')
BLOCKCHAIN_BASE_URL = "https://on-shop-blockchain.onrender.com"
API_KEY = 'dCQEI4C7ADRvlx-c7_1dNRP8dcESHa9kBsaQ2Lf5zXU='
PARTNER_CODE = 'fc193dfc78009398babab0c25ce79a29'
cart = APIRouter()


def create_signature(body, api_key):
    message = json.dumps(body) + api_key
    signature = hmac.new(config.SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
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
    try:
        if order is None:
            print('order is none')
        print('order: ',order)
        amount = order['amount']
        currency = order['currency']
        # call api
        data = {
            'amount': amount,
            'currency': currency,
            'order_id': secrets.token_hex(12)
        }
        sign = create_signature(data, API_KEY)
        headers = {
            'merchant': PARTNER_CODE,
            'sign': sign
        }

        async with httpx.AsyncClient(base_url=BLOCKCHAIN_BASE_URL, headers=headers) as client:
            response = await client.post("/get_order_input", json=order)
            return response.json()
    except:
        return {'success': False}


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
