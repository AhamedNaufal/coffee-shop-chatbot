from repositories.database import Database
from repositories.schema.schema import Item, Order, OrderItemMapping



class ChatbotRepository:
    def __init__(self):
        self.db_instance = Database()
    def check_order_status_repo(self,order_id) :
        db=None
        try:
            db = self.db_instance.SessionLocal()
            order = db.query(Order).filter(Order.order_id == order_id).first()
            if not order:
                return None
            return order.order_status
        except Exception as e:
            
            print("Error in repo",str(e))
            if db:
                db.rollback()
            return None
        finally:
             if db:
                db.close()
    
    def check_inventory_repo(self,item_name) :
        db=None
        try:
            db = self.db_instance.SessionLocal()
            inventory = db.query(Item).filter(Item.item_name.ilike(f"%{item_name}%")).first()
            if not inventory:
                return None
            return inventory.stock_availability
        except Exception as e:
            print("Error in repo",str(e))
            if db:
                db.rollback()
            return None
        finally:
             if db:
                db.close()

    def check_menu_repo(self):
        db=None
        try:
            db = self.db_instance.SessionLocal()
            item = db.query(Item).all()
            menu = []
            for items in item:
                menu.append({
                    "name":items.item_name,
                    "price":items.item_price
                })
           
            return menu
        except Exception as e:
            print("Error in repo",str(e))
            if db:
                db.rollback()
            return None
            
        finally:
             if db:
                db.close()
  

    def place_order_repo(self,customer_id, items):
        db=None
        try:
            db = self.db_instance.SessionLocal()
            total = 0
            added=0
            order = Order(customer_id = customer_id)
            db.add(order)
            db.flush()
            for item in items:
                name = item["item_name"]
                quantity = int(item["quantity"])
                if quantity <=0:
                    continue
                item = db.query(Item).filter(Item.item_name.ilike(f"%{name}%")).first()
                if item:
                    total += float(item.item_price)* quantity
                    mapping = OrderItemMapping(
                        order_id = order.order_id,
                        item_id = item.item_id,
                        quantity = quantity
                    )
                    added +=1
                    db.add(mapping)

            if added == 0:
                db.rollback()
                return None
            
            db.commit()
            return {
                "order_id" : order.order_id,
                "total_price": total,
                "items": items
            }
        except Exception as e:
            print("Error in repo",str(e))
            if db:
                db.rollback()
            return None
            
        finally:
             if db:
                db.close()
    
        
        
    