from upload_ml_attachments_DB_day_orders import insert_carrier_tracking_ref_odoo, insert_LOIN_carrier_odoo, get_odoo_model
from upload_ml_attachments_DB_day_orders import get_db_connection
import time as tm



def get_orders_info_DB(so_names):
    if not so_names:
        return []

    connection = get_db_connection()
    cursor = connection.cursor()

    placeholders = ', '.join(['%s'] * len(so_names))

    query = f"""
        SELECT id, order_id, so_name, marketplace_reference, seller_marketplace, 
               ml_status, carrier_tracking_ref, pick_id, status
        FROM ml_guide_insertion
        WHERE so_name IN ({placeholders})
    """

    cursor.execute(query, tuple(so_names))
    results = cursor.fetchall()

    orders = [
        {
            "id": row[0],
            "order_id": row[1],
            "so_name": row[2],
            "marketplace_reference": row[3],
            "seller_marketplace": row[4],
            "ml_status": row[5],
            "carrier_tracking_ref": row[6],
            "pick_id": row[7],
            "status": row[8]
        }
        for row in results
    ]

    cursor.close()
    connection.close()

    return orders






if __name__ == "__main__":
    get_odoo_model(environment=False)

    order_list = [
                "SO3589420", "SO3589695", "SO3593960", "SO3594244", "SO3594629",
                "SO3595031", "SO3597817", "SO3597818", "SO3597820", "SO3597822",
                "SO3597828", "SO3597829", "SO3597834", "SO3597836", "SO3597837",
                "SO3597839", "SO3597843", "SO3597846", "SO3597848", "SO3597849",
                "SO3597850", "SO3597851", "SO3597857", "SO3597858", "SO3597862",
                "SO3597867", "SO3597874", "SO3597879", "SO3597883", "SO3597887",
                "SO3597890", "SO3597893", "SO3597922", "SO3597926", "SO3597931",
                "SO3597935", "SO3597937", "SO3597940", "SO3597941", "SO3597942",
                "SO3597947", "SO3597948", "SO3597954", "SO3597971", "SO3597972",
                "SO3597981", "SO3597347", "SO3597349", "SO3597351", "SO3597361",
                "SO3597418", "SO3597466", "SO3597549", "SO3597559", "SO3597562",
                "SO3597629", "SO3597637", "SO3597683", "SO3597691", "SO3597692",
                "SO3597703", "SO3597708", "SO3597714", "SO3597724", "SO3597737",
                "SO3597777", "SO3583654"
            ]

    order_list_flex = ["SO3597858", "SO3597466"]

    db_orders = get_orders_info_DB(order_list_flex)
    print(db_orders)

    for order in db_orders:
        print(order)
        record_id = order["id"]  # Registro de la DB

        order_id = int(order['order_id'])
        so_name = order['so_name']
        marketplace_reference = order['marketplace_reference']
        seller_marketplace = order['seller_marketplace']
        carrier_tracking_ref = order['carrier_tracking_ref']  # Colecta
        pick_id = int(order['pick_id'])
        ml_crawl_status = order["ml_status"]

        # response = insert_carrier_tracking_ref_odoo(order_id, so_name, carrier_tracking_ref)
        response = insert_LOIN_carrier_odoo(order_id, so_name)
        print(response)


