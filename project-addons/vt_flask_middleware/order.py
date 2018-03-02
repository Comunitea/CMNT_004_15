# -*- coding: utf-8 -*-
from peewee import CharField, IntegerField, DateTimeField, ForeignKeyField, DecimalField
from app import app
from customer import Customer
from product import Product
from database import SyncModel


class Order(SyncModel):
    odoo_id = IntegerField(unique=True)
    name = CharField(max_length=30)
    state = CharField(max_length=15)
    partner_id = ForeignKeyField(Customer, on_delete="CASCADE")
    amount_total= DecimalField(max_digits=2, decimal_places=2, rounding='ROUND_HALF_EVEN')
    amount_untaxed = DecimalField(max_digits=2, decimal_places=2, rounding='ROUND_HALF_EVEN')
    date_order = DateTimeField(formats=['%Y-%m-%d %H:%M:%S'])
    client_order_ref = CharField(max_length=50, null=True)
    shipping_street = CharField(max_length=100, null=True)
    shipping_zip = CharField(max_length=10, null=True)
    shipping_city = CharField(max_length=50, null=True)
    shipping_state = CharField(max_length=30, null=True)
    shipping_country = CharField(max_length=50, null=True)

    MOD_NAME = 'order'

    def __unicode__(self):
        return u'%s' % self.name


class OrderProduct(SyncModel):
    odoo_id = IntegerField(unique=True)
    product_id = ForeignKeyField(Product, on_delete='CASCADE')
    product_qty = IntegerField()
    price_subtotal = DecimalField(max_digits=2, decimal_places=2, rounding='ROUND_HALF_EVEN')
    order_id = ForeignKeyField(Order, on_delete='CASCADE')

    MOD_NAME = 'orderproduct'

    def __unicode__(self):
        return u'%s - %s' % (self.product_id, self.order_id)