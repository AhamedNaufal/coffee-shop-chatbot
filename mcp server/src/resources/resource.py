import json
import os

from fastmcp.resources import ResourceContent

from repositories.mcp_server_repository import ChatbotRepository
from routes.mcp_server_router import mcp_router
repository=ChatbotRepository()
@mcp_router.resource("menu://items")
def get_menu():
    """ List all the menu item"""
    menu = repository.check_menu_repo()
    return [ResourceContent(content = str(menu))]

@mcp_router.resource("shop://location")
def get_location():
    path = os.path.join(os.path.dirname(__file__),"location.json")
    with open(path,"r") as f:
        data = json.load(f)
    return [ResourceContent(content = str(data))]