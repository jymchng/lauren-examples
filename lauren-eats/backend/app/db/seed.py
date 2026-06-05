"""Database seed — 8 categories and 42 menu items + sample orders."""

from __future__ import annotations

import uuid
import random
import string
import time
from datetime import datetime, timedelta


def _new_id() -> str:
    return uuid.uuid4().hex[:25]


CATEGORIES = [
    {"id": _new_id(), "name": "Appetizers", "name_zh": "开胃菜", "slug": "appetizers", "description": "Light starters to awaken your palate", "icon": "🥟", "sort_order": 1},
    {"id": _new_id(), "name": "Soups", "name_zh": "汤类", "slug": "soups", "description": "Comforting bowls of traditional Chinese soups", "icon": "🍲", "sort_order": 2},
    {"id": _new_id(), "name": "Dim Sum", "name_zh": "点心", "slug": "dim-sum", "description": "Cantonese-style bite-sized delicacies", "icon": "🫔", "sort_order": 3},
    {"id": _new_id(), "name": "Main Courses - Meat", "name_zh": "荤菜", "slug": "main-meat", "description": "Hearty meat dishes prepared with authentic techniques", "icon": "🥩", "sort_order": 4},
    {"id": _new_id(), "name": "Main Courses - Seafood", "name_zh": "海鲜", "slug": "main-seafood", "description": "Fresh seafood crafted with classic Chinese flavors", "icon": "🦐", "sort_order": 5},
    {"id": _new_id(), "name": "Main Courses - Vegetable", "name_zh": "素菜", "slug": "main-vegetable", "description": "Flavorful vegetable dishes for the health-conscious", "icon": "🥬", "sort_order": 6},
    {"id": _new_id(), "name": "Rice & Noodles", "name_zh": "饭面", "slug": "rice-noodles", "description": "Staple dishes of rice and noodles with savory accompaniments", "icon": "🍜", "sort_order": 7},
    {"id": _new_id(), "name": "Desserts", "name_zh": "甜品", "slug": "desserts", "description": "Sweet endings with a Chinese twist", "icon": "🍮", "sort_order": 8},
]

MENU_ITEMS = {
    "appetizers": [
        {"name": "Spring Rolls", "name_zh": "春卷", "description": "Crispy golden rolls filled with shredded vegetables and glass noodles, served with sweet chili sauce", "price": 8.99, "image": "🥟", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 0, "is_popular": 1, "calories": 220, "preparation_time": 10, "ingredients": '["cabbage","carrots","glass noodles","shiitake mushrooms","spring roll wrapper"]', "allergens": '["wheat","soy"]', "tags": '["crispy","classic","shareable"]'},
        {"name": "Edamame", "name_zh": "毛豆", "description": "Steamed young soybeans tossed with coarse sea salt, a simple and healthy starter", "price": 6.99, "image": "🫛", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 120, "preparation_time": 5, "ingredients": '["edamame","sea salt"]', "allergens": '["soy"]', "tags": '["healthy","light","quick"]'},
        {"name": "Scallion Pancakes", "name_zh": "葱油饼", "description": "Flaky, layered flatbread studded with scallions, pan-fried to golden perfection", "price": 7.99, "image": "🫓", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 280, "preparation_time": 12, "ingredients": '["flour","scallions","sesame oil","salt"]', "allergens": '["wheat","sesame"]', "tags": '["crispy","classic","comfort"]'},
        {"name": "Spicy Wontons in Chili Oil", "name_zh": "红油抄手", "description": "Pork-filled wontons bathed in a fiery chili oil sauce with black vinegar and garlic", "price": 10.99, "image": "🌶️", "spicy_level": 3, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 320, "preparation_time": 15, "ingredients": '["pork","wonton wrapper","chili oil","black vinegar","garlic","scallions"]', "allergens": '["wheat","soy","pork"]', "tags": '["spicy","signature","Sichuan"]'},
        {"name": "Cucumber Salad with Garlic", "name_zh": "蒜泥黄瓜", "description": "Refreshing smashed cucumber salad dressed with garlic, vinegar, and a hint of sesame oil", "price": 6.49, "image": "🥒", "spicy_level": 1, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 80, "preparation_time": 5, "ingredients": '["cucumber","garlic","rice vinegar","sesame oil","chili flakes"]', "allergens": '["sesame"]', "tags": '["refreshing","light","healthy"]'},
    ],
    "soups": [
        {"name": "Hot and Sour Soup", "name_zh": "酸辣汤", "description": "A bold, tangy broth with tofu, bamboo shoots, wood ear mushrooms, and egg ribbons", "price": 9.99, "image": "🍲", "spicy_level": 2, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 150, "preparation_time": 15, "ingredients": '["tofu","bamboo shoots","wood ear mushrooms","egg","white pepper","rice vinegar"]', "allergens": '["egg","soy"]', "tags": '["classic","warming","tangy"]'},
        {"name": "Wonton Soup", "name_zh": "馄饨汤", "description": "Delicate shrimp and pork wontons in a clear, savory chicken broth with bok choy", "price": 10.99, "image": "🥟", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 260, "preparation_time": 15, "ingredients": '["shrimp","pork","wonton wrapper","chicken broth","bok choy"]', "allergens": '["wheat","shellfish","soy"]', "tags": '["comfort","classic","light"]'},
        {"name": "Egg Drop Soup", "name_zh": "蛋花汤", "description": "Silky smooth chicken broth with delicate egg ribbons and a touch of white pepper", "price": 7.49, "image": "🥚", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 100, "preparation_time": 8, "ingredients": '["chicken broth","egg","cornstarch","white pepper","scallions"]', "allergens": '["egg"]', "tags": '["comfort","light","quick"]'},
        {"name": "Tom Yum Seafood Soup", "name_zh": "冬阴功海鲜汤", "description": "A fragrant, spicy and sour Thai-inspired soup with shrimp, squid, and mushrooms", "price": 13.99, "image": "🦐", "spicy_level": 3, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 180, "preparation_time": 18, "ingredients": '["shrimp","squid","mushrooms","lemongrass","galangal","lime leaves","chili"]', "allergens": '["shellfish"]', "tags": '["spicy","tangy","seafood"]'},
    ],
    "dim-sum": [
        {"name": "Har Gow", "name_zh": "虾饺", "description": "Translucent crystal shrimp dumplings, a dim sum classic with a delicate wrapper", "price": 11.99, "image": "🫔", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 200, "preparation_time": 20, "ingredients": '["shrimp","tapioca starch","bamboo shoots","pork fat"]', "allergens": '["shellfish","pork"]', "tags": '["classic","Cantonese","steamed"]'},
        {"name": "Siu Mai", "name_zh": "烧卖", "description": "Open-topped pork and shrimp dumplings topped with crab roe, steamed to perfection", "price": 10.99, "image": "🥟", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 230, "preparation_time": 18, "ingredients": '["pork","shrimp","crab roe","wonton wrapper","ginger"]', "allergens": '["wheat","shellfish","pork"]', "tags": '["classic","Cantonese","steamed"]'},
        {"name": "BBQ Pork Buns", "name_zh": "叉烧包", "description": "Fluffy steamed buns filled with sweet and savory char siu pork", "price": 9.99, "image": "🥩", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 290, "preparation_time": 20, "ingredients": '["pork","flour","sugar","soy sauce","hoisin sauce","sesame oil"]', "allergens": '["wheat","soy","sesame","pork"]', "tags": '["classic","Cantonese","steamed","sweet"]'},
        {"name": "Vegetable Dumplings", "name_zh": "素饺", "description": "Pan-fried dumplings filled with shiitake mushrooms, cabbage, and glass noodles", "price": 9.49, "image": "🥬", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 0, "is_popular": 0, "calories": 180, "preparation_time": 15, "ingredients": '["shiitake mushrooms","cabbage","glass noodles","dumpling wrapper","ginger","soy sauce"]', "allergens": '["wheat","soy"]', "tags": '["vegetarian","pan-fried","healthy"]'},
        {"name": "Turnip Cake", "name_zh": "萝卜糕", "description": "Pan-seared daikon radish cake with dried shrimp and Chinese sausage, crispy on the outside", "price": 8.99, "image": "🫓", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 250, "preparation_time": 15, "ingredients": '["daikon radish","rice flour","dried shrimp","Chinese sausage","scallions"]', "allergens": '["shellfish"]', "tags": '["classic","Cantonese","pan-fried"]'},
    ],
    "main-meat": [
        {"name": "Kung Pao Chicken", "name_zh": "宫保鸡丁", "description": "Wok-fired chicken cubes with peanuts, dried chilies, and Sichuan peppercorns in a sweet-savory glaze", "price": 16.99, "image": "🍗", "spicy_level": 3, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 420, "preparation_time": 20, "ingredients": '["chicken breast","peanuts","dried chilies","Sichuan peppercorns","soy sauce","black vinegar"]', "allergens": '["peanuts","soy","wheat"]', "tags": '["spicy","Sichuan","signature","classic"]'},
        {"name": "Twice-Cooked Pork", "name_zh": "回锅肉", "description": "Sliced pork belly stir-fried with fermented chili bean paste, leeks, and garlic sprouts", "price": 17.99, "image": "🥩", "spicy_level": 2, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 480, "preparation_time": 22, "ingredients": '["pork belly","fermented chili bean paste","leeks","garlic sprouts","ginger"]', "allergens": '["soy","pork"]', "tags": '["Sichuan","classic","flavorful"]'},
        {"name": "Crispy Peking Duck", "name_zh": "北京烤鸭", "description": "Iconic roasted duck with lacquered crispy skin, served with pancakes, hoisin sauce, and scallions", "price": 38.99, "image": "🦆", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 680, "preparation_time": 45, "ingredients": '["duck","hoisin sauce","pancakes","scallions","cucumber"]', "allergens": '["wheat","soy"]', "tags": '["signature","premium","Beijing","celebration"]'},
        {"name": "Mapo Tofu with Pork", "name_zh": "麻婆豆腐", "description": "Silken tofu in a fiery, numbing chili bean sauce with minced pork and Sichuan peppercorns", "price": 14.99, "image": "🌶️", "spicy_level": 4, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 320, "preparation_time": 18, "ingredients": '["silken tofu","pork","fermented chili bean paste","Sichuan peppercorns","garlic","scallions"]', "allergens": '["soy","pork"]', "tags": '["spicy","Sichuan","signature","classic"]'},
        {"name": "Sweet and Sour Pork", "name_zh": "糖醋里脊", "description": "Crispy battered pork loin glazed in a vibrant sweet and sour sauce with bell peppers and pineapple", "price": 15.99, "image": "🍖", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 460, "preparation_time": 20, "ingredients": '["pork loin","pineapple","bell peppers","rice vinegar","sugar","ketchup"]', "allergens": '["wheat","soy","pork"]', "tags": '["sweet","classic","crispy","family"]'},
        {"name": "Black Pepper Beef", "name_zh": "黑椒牛柳", "description": "Tender beef tenderloin strips wok-tossed with onions and bell peppers in a bold black pepper sauce", "price": 19.99, "image": "🥩", "spicy_level": 1, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 0, "calories": 440, "preparation_time": 18, "ingredients": '["beef tenderloin","black pepper","onions","bell peppers","oyster sauce","soy sauce"]', "allergens": '["wheat","soy"]', "tags": '["savory","premium","wok-hei"]'},
        {"name": "Lion's Head Meatballs", "name_zh": "狮子头", "description": "Jumbo pork meatballs braised in a rich soy-based broth with napa cabbage, tender and juicy", "price": 16.49, "image": "🍖", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 520, "preparation_time": 30, "ingredients": '["pork","napa cabbage","ginger","soy sauce","rice wine","scallions"]', "allergens": '["soy","pork"]', "tags": '["comfort","Jiangnan","braised"]'},
    ],
    "main-seafood": [
        {"name": "Steamed Fish with Ginger and Scallion", "name_zh": "清蒸鲈鱼", "description": "Whole sea bass gently steamed and topped with julienned ginger, scallions, and hot soy oil", "price": 26.99, "image": "🐟", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 300, "preparation_time": 25, "ingredients": '["sea bass","ginger","scallions","soy sauce","sesame oil"]', "allergens": '["fish","soy","sesame"]', "tags": '["Cantonese","premium","fresh","healthy"]'},
        {"name": "Salt and Pepper Shrimp", "name_zh": "椒盐虾", "description": "Crispy deep-fried shrimp tossed with sea salt, white pepper, garlic, and chili", "price": 19.99, "image": "🦐", "spicy_level": 2, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 380, "preparation_time": 18, "ingredients": '["shrimp","garlic","chili","sea salt","white pepper","flour"]', "allergens": '["shellfish","wheat"]', "tags": '["crispy","signature","shareable"]'},
        {"name": "Szechuan Boiled Fish", "name_zh": "水煮鱼", "description": "Tender fish fillets submerged in a blazing bath of chili oil with Sichuan peppercorns and bean sprouts", "price": 22.99, "image": "🌶️", "spicy_level": 5, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 450, "preparation_time": 25, "ingredients": '["fish fillet","chili oil","Sichuan peppercorns","bean sprouts","fermented chili bean paste","garlic"]', "allergens": '["fish","soy"]', "tags": '["spicy","Sichuan","signature","adventurous"]'},
        {"name": "Garlic Butter Crab", "name_zh": "蒜蓉螃蟹", "description": "Whole crab wok-tossed in a rich garlic butter sauce with a hint of chili and Shaoxing wine", "price": 34.99, "image": "🦀", "spicy_level": 1, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 400, "preparation_time": 30, "ingredients": '["crab","garlic","butter","Shaoxing wine","chili","scallions"]', "allergens": '["shellfish","dairy"]', "tags": '["premium","celebration","garlic"]'},
        {"name": "Honey Walnut Shrimp", "name_zh": "核桃虾", "description": "Crispy shrimp coated in a creamy honey sauce topped with candied walnuts, a crowd favorite", "price": 21.99, "image": "🍯", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 520, "preparation_time": 18, "ingredients": '["shrimp","walnuts","honey","mayonnaise","sweetened condensed milk","flour"]', "allergens": '["shellfish","tree nuts","wheat","dairy","egg"]', "tags": '["sweet","creamy","popular","family"]'},
    ],
    "main-vegetable": [
        {"name": "Braised Tofu with Mushrooms", "name_zh": "红烧豆腐", "description": "Golden pan-fried tofu braised with shiitake mushrooms in a rich soy-based sauce", "price": 12.99, "image": "🧈", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 1, "calories": 220, "preparation_time": 15, "ingredients": '["tofu","shiitake mushrooms","soy sauce","ginger","scallions","sesame oil"]', "allergens": '["soy","sesame"]', "tags": '["vegetarian","vegan","comfort","healthy"]'},
        {"name": "Stir-Fried Bok Choy with Garlic", "name_zh": "蒜蓉小白菜", "description": "Tender baby bok choy quickly wok-tossed with garlic and a splash of oyster sauce", "price": 10.99, "image": "🥬", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 90, "preparation_time": 8, "ingredients": '["baby bok choy","garlic","oyster sauce","vegetable oil"]', "allergens": '["soy"]', "tags": '["light","healthy","quick"]'},
        {"name": "Dry-Fried Green Beans", "name_zh": "干煸四季豆", "description": "Flash-fried green beans with garlic, ginger, and a touch of chili for a smoky char", "price": 11.99, "image": "🫘", "spicy_level": 1, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 1, "calories": 160, "preparation_time": 12, "ingredients": '["green beans","garlic","ginger","dried chilies","soy sauce"]', "allergens": '["soy"]', "tags": '["vegetarian","vegan","wok-hei","smoky"]'},
        {"name": "Eggplant in Garlic Sauce", "name_zh": "鱼香茄子", "description": "Velvety braised eggplant in a tangy, savory garlic sauce with hints of chili and sweet bean paste", "price": 12.49, "image": "🍆", "spicy_level": 2, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 200, "preparation_time": 18, "ingredients": '["eggplant","garlic","ginger","chili bean paste","soy sauce","rice vinegar"]', "allergens": '["soy"]', "tags": '["vegetarian","vegan","Sichuan","savory"]'},
        {"name": "Buddha's Delight", "name_zh": "罗汉斋", "description": "A medley of tofu, mushrooms, bamboo shoots, and vegetables in a light savory broth", "price": 13.99, "image": "🧘", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 180, "preparation_time": 20, "ingredients": '["tofu","shiitake mushrooms","bamboo shoots","baby corn","snow peas","ginger","soy sauce"]', "allergens": '["soy"]', "tags": '["vegetarian","vegan","traditional","healthy"]'},
    ],
    "rice-noodles": [
        {"name": "Yangzhou Fried Rice", "name_zh": "扬州炒饭", "description": "Wok-fried rice with shrimp, char siu, egg, peas, and scallions — the gold standard of fried rice", "price": 13.99, "image": "🍚", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 520, "preparation_time": 15, "ingredients": '["rice","shrimp","char siu","egg","peas","scallions","soy sauce"]', "allergens": '["shellfish","egg","soy","pork"]', "tags": '["classic","wok-hei","signature"]'},
        {"name": "Dan Dan Noodles", "name_zh": "担担面", "description": "Chewy noodles topped with spiced pork, chili oil, Sichuan peppercorns, and preserved vegetables", "price": 12.99, "image": "🍜", "spicy_level": 4, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 480, "preparation_time": 15, "ingredients": '["wheat noodles","pork","chili oil","Sichuan peppercorns","sesame paste","preserved vegetables"]', "allergens": '["wheat","soy","sesame","pork"]', "tags": '["spicy","Sichuan","signature","noodles"]'},
        {"name": "Beef Chow Fun", "name_zh": "干炒牛河", "description": "Wide rice noodles wok-tossed with tender beef slices, bean sprouts, and dark soy — smoky and satisfying", "price": 14.99, "image": "🍝", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 540, "preparation_time": 15, "ingredients": '["rice noodles","beef","bean sprouts","dark soy sauce","scallions"]', "allergens": '["soy"]', "tags": '["Cantonese","wok-hei","classic","comfort"]'},
        {"name": "Shrimp Lo Mein", "name_zh": "虾捞面", "description": "Soft egg noodles tossed with plump shrimp, bok choy, and a light savory sauce", "price": 13.49, "image": "🍜", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 0, "calories": 460, "preparation_time": 12, "ingredients": '["egg noodles","shrimp","bok choy","soy sauce","sesame oil","scallions"]', "allergens": '["wheat","shellfish","soy","sesame","egg"]', "tags": '["classic","comfort","noodles"]'},
        {"name": "Vegetable Fried Rice", "name_zh": "素炒饭", "description": "Light and fluffy wok-fried rice with mixed vegetables, egg, and scallions", "price": 11.49, "image": "🍚", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 0, "calories": 380, "preparation_time": 12, "ingredients": '["rice","egg","carrots","peas","corn","scallions","soy sauce"]', "allergens": '["egg","soy"]', "tags": '["vegetarian","light","classic"]'},
        {"name": "Wonton Noodle Soup", "name_zh": "云吞面", "description": "Thin egg noodles in a clear broth topped with plump shrimp and pork wontons", "price": 12.49, "image": "🥟", "spicy_level": 0, "is_vegetarian": 0, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 390, "preparation_time": 15, "ingredients": '["egg noodles","shrimp","pork","wonton wrapper","chicken broth","scallions"]', "allergens": '["wheat","shellfish","soy","pork","egg"]', "tags": '["Cantonese","comfort","soup","classic"]'},
    ],
    "desserts": [
        {"name": "Mango Pudding", "name_zh": "芒果布丁", "description": "Silky smooth mango pudding topped with fresh mango cubes and a drizzle of coconut cream", "price": 7.99, "image": "🥭", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 0, "is_gluten_free": 1, "is_popular": 1, "calories": 200, "preparation_time": 5, "ingredients": '["mango","coconut cream","gelatin","sugar"]', "allergens": '["coconut"]', "tags": '["sweet","tropical","refreshing"]'},
        {"name": "Sesame Balls", "name_zh": "芝麻球", "description": "Crispy fried mochi balls coated in sesame seeds with a sweet red bean paste filling", "price": 6.99, "image": "🟤", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 1, "calories": 280, "preparation_time": 12, "ingredients": '["glutinous rice flour","red bean paste","sesame seeds","sugar"]', "allergens": '["sesame"]', "tags": '["crispy","traditional","sweet"]'},
        {"name": "Egg Tarts", "name_zh": "蛋挞", "description": "Flaky pastry shells filled with silky egg custard, a beloved Hong Kong classic", "price": 6.49, "image": "🥧", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 0, "is_gluten_free": 0, "is_popular": 1, "calories": 220, "preparation_time": 10, "ingredients": '["flour","egg","sugar","milk","butter"]', "allergens": '["wheat","egg","dairy"]', "tags": '["Cantonese","classic","baked"]'},
        {"name": "Red Bean Soup", "name_zh": "红豆沙", "description": "Warm, comforting sweet red bean soup with dried tangerine peel and lotus seeds", "price": 5.99, "image": "🫘", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 180, "preparation_time": 8, "ingredients": '["red beans","sugar","dried tangerine peel","lotus seeds"]', "allergens": '[]', "tags": '["traditional","comfort","warm","vegan"]'},
        {"name": "Almond Tofu", "name_zh": "杏仁豆腐", "description": "Delicate almond-flavored tofu pudding served chilled with lychee and goji berries", "price": 6.99, "image": "🥛", "spicy_level": 0, "is_vegetarian": 1, "is_vegan": 1, "is_gluten_free": 1, "is_popular": 0, "calories": 150, "preparation_time": 5, "ingredients": '["almond milk","agar-agar","sugar","lychee","goji berries"]', "allergens": '["tree nuts"]', "tags": '["refreshing","light","traditional"]'},
    ],
}


async def run_seed(db) -> dict:
    """Seed the database with categories, menu items, and sample orders."""
    # Check if already seeded
    existing = await db.fetch_count("SELECT COUNT(*) FROM categories")
    if existing > 0:
        return {"message": "Database already seeded", "categories": existing, "items": 0}

    # Insert categories
    category_map = {}
    for cat in CATEGORIES:
        await db.execute(
            """INSERT INTO categories (id, name, name_zh, slug, description, icon, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (cat["id"], cat["name"], cat["name_zh"], cat["slug"], cat["description"], cat["icon"], cat["sort_order"]),
        )
        category_map[cat["slug"]] = cat["id"]

    # Insert menu items
    total_items = 0
    for slug, items in MENU_ITEMS.items():
        cat_id = category_map.get(slug)
        if not cat_id:
            continue
        for item in items:
            await db.execute(
                """INSERT INTO menu_items
                   (id, name, name_zh, description, price, image, category_id,
                    spicy_level, is_vegetarian, is_vegan, is_gluten_free, is_popular, is_available,
                    calories, preparation_time, ingredients, allergens, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
                (_new_id(), item["name"], item["name_zh"], item["description"],
                 item["price"], item["image"], cat_id,
                 item["spicy_level"], item["is_vegetarian"], item["is_vegan"],
                 item["is_gluten_free"], item["is_popular"],
                 item["calories"], item["preparation_time"],
                 item["ingredients"], item["allergens"], item["tags"]),
            )
            total_items += 1

    # Sample orders
    all_items = await db.fetch_all("SELECT id, price FROM menu_items")
    if not all_items:
        return {"categories": len(CATEGORIES), "items": total_items, "orders": 0}

    sample_configs = [
        {"type": "dine_in", "status": "delivered", "table_number": "5", "notes": "No MSG please", "days_ago": 5, "indices": [0, 5, 12], "quantities": [2, 1, 1]},
        {"type": "takeout", "status": "delivered", "table_number": None, "notes": None, "days_ago": 3, "indices": [3, 8, 15], "quantities": [1, 2, 1]},
        {"type": "dine_in", "status": "ready", "table_number": "12", "notes": "Extra spicy on the side", "days_ago": 0, "indices": [2, 7, 20], "quantities": [1, 1, 2]},
        {"type": "delivery", "status": "preparing", "table_number": None, "notes": "Leave at the door", "days_ago": 0, "indices": [1, 10, 18], "quantities": [3, 1, 1]},
        {"type": "dine_in", "status": "confirmed", "table_number": "3", "notes": "Birthday celebration", "days_ago": 0, "indices": [4, 11, 25], "quantities": [1, 1, 1]},
        {"type": "takeout", "status": "pending", "table_number": None, "notes": "Call when ready", "days_ago": 0, "indices": [6, 13, 30], "quantities": [2, 1, 1]},
        {"type": "delivery", "status": "cancelled", "table_number": None, "notes": "Customer cancelled", "days_ago": 2, "indices": [0, 9, 22], "quantities": [1, 1, 1]},
        {"type": "dine_in", "status": "delivered", "table_number": "8", "notes": None, "days_ago": 7, "indices": [5, 16, 28], "quantities": [1, 2, 1]},
    ]

    order_count = 0
    for cfg in sample_configs:
        order_items = []
        for i, idx in enumerate(cfg["indices"]):
            mi = all_items[idx % len(all_items)]
            qty = cfg["quantities"][i]
            total_price = round(mi["price"] * qty, 2)
            order_items.append({"menu_item_id": mi["id"], "quantity": qty, "unit_price": mi["price"], "total_price": total_price})

        subtotal = round(sum(oi["total_price"] for oi in order_items), 2)
        tax = round(subtotal * 0.08, 2)
        total_amount = round(subtotal + tax, 2)

        order_id = _new_id()
        order_number = f"LE-{hex(int(time.time()))[2:].upper()}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

        created = datetime.now() - timedelta(days=cfg["days_ago"])

        await db.execute(
            """INSERT INTO orders (id, order_number, status, total_amount, subtotal, tax, discount, notes, type, table_number, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
            (order_id, order_number, cfg["status"], total_amount, subtotal, tax,
             cfg["notes"], cfg["type"], cfg["table_number"], created.isoformat()),
        )

        for oi in order_items:
            await db.execute(
                """INSERT INTO order_items (id, order_id, menu_item_id, quantity, unit_price, total_price)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (_new_id(), order_id, oi["menu_item_id"], oi["quantity"], oi["unit_price"], oi["total_price"]),
            )
        order_count += 1

    return {
        "categories": len(CATEGORIES),
        "items": total_items,
        "orders": order_count,
        "message": f"Seeded {len(CATEGORIES)} categories, {total_items} menu items, {order_count} orders",
    }
