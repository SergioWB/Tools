from upload_ml_attachments_DB_day_orders import *
from dotenv import load_dotenv
from datetime import datetime, timedelta
import os
import xmlrpc.client
import time as tm

load_dotenv()


if __name__ == "__main__":

    start_date, end_date = get_local_utc_range()

    print(start_date, end_date)

    enviroment = 'production'

    get_odoo_model(enviroment)

    filter_date = get_latest_date_from_db().strftime('%Y-%m-%d %H:%M:%S')
    now_date = datetime.now()
    today_date = now_date.strftime('%Y-%m-%d %H:%M:%S')


    odoo_orders = get_orders_from_odoo(filter_date, today_date)
    # for order in odoo_orders:
    #     print(order['name'], order['channel_order_reference'])

    print("//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////")

    db_orders = get_orders_day_info_crawl(start_date, end_date)
    # for order in orders:
    #     print(order)

    final_orders = filter_matching_orders(odoo_orders, db_orders)
    for order in final_orders:
        print(order)