from upload_ml_attachments_DB_day_orders import get_db_connection_server0, get_db_connection


def get_orders_day_info_crawl():
    connection = get_db_connection_server0()
    cursor = connection.cursor()


    query = f"""
                SELECT status_name, sub_status_name, txn_id_mp, inserted_at
                FROM (
                    SELECT *, ROW_NUMBER() OVER (PARTITION BY txn_id_mp ORDER BY inserted_at DESC) AS rn
                    FROM ml_sr_orders_h
                    WHERE inserted_at >= '2025-03-01 23:00:00'
                    AND inserted_at < '2025-03-12 23:00:00' 
                ) t
                WHERE rn = 1;
                """

    cursor.execute(query)
    results = cursor.fetchall()

    orders = [
        {
            "status_name": row[0],
            "sub_status_name": row[1],
            "txn_id_mp": row[2],
            "inserted_at": row[3],
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    print(f"{len(orders)} registros en la DB ML")

    return orders


def get_orders_info_DB():
    connection = get_db_connection()
    cursor = connection.cursor()



    query = """
        select id, order_id, so_name, marketplace_reference, seller_marketplace, ml_status, carrier_tracking_ref, pick_id, status
        from tools.ml_guide_insertion
        WHERE last_update_DB > '2025-03-01 23:00:00'
        AND ml_status = 'Envíos de hoy'
        AND processed_successfully = 0
        AND already_printed = 0
    """

    cursor.execute(query)
    results = cursor.fetchall()

    orders = [
        {
            "id": row[0],
            "order_id": int(row[1]),
            "so_name": row[2],
            "marketplace_reference": row[3],
            "seller_marketplace": row[4],
            "ml_status": row[5],
            "carrier_tracking_ref": row[6],
            "pick_id": int(row[7]),
            "status": row[8]
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    print(f"{len(orders)} órdenes pendientes en DB")

    return orders


if __name__ == "__main__":
    crawl_orders = get_orders_day_info_crawl()
    tools_orders = get_orders_info_DB()

    for order in crawl_orders:
        print(order)

    print('----------------------------------------------')

    for order in tools_orders:
        print(order)