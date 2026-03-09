#!/usr/bin/env python
import asyncio
import os
from mcp.server import FastMCP

from .data.recipes import fetch_recipes, get_all_categories

# 创建MCP服务器
app = FastMCP(
    name="howtocook-py-mcp",
    instructions="菜谱助手 MCP 服务",
    port=9000
)

# 获取所有菜谱工具
@app.tool()
async def get_all_recipes():
    """
    获取所有菜谱

    Returns:
        所有菜谱的简化信息，只包含名称和描述
    """
    # 获取菜谱数据
    from .utils.recipe_utils import simplify_recipe_name_only
    
    recipes = await fetch_recipes()
    if not recipes:
        return "未能获取菜谱数据"
    
    # 返回更简化版的菜谱数据，只包含name和description
    simplified_recipes = [simplify_recipe_name_only(recipe) for recipe in recipes]
    
    # 返回JSON字符串
    import json
    return json.dumps([recipe.model_dump() for recipe in simplified_recipes], 
                     ensure_ascii=False, indent=2)

# 按分类获取菜谱工具
@app.tool()
async def get_recipes_by_category(category: str):
    """
    根据分类查询菜谱
    
    Args:
        category: 菜谱分类名称，如水产、早餐、荤菜、主食等
        
    Returns:
        该分类下所有菜谱的简化信息
    """
    from .utils.recipe_utils import simplify_recipe
    
    recipes = await fetch_recipes()
    if not recipes:
        return "未能获取菜谱数据"
    
    # 过滤出指定分类的菜谱
    filtered_recipes = [recipe for recipe in recipes if recipe.category == category]
    
    # 返回简化版的菜谱数据
    simplified_recipes = [simplify_recipe(recipe) for recipe in filtered_recipes]
    
    # 返回JSON字符串
    import json
    return json.dumps([recipe.model_dump() for recipe in simplified_recipes], 
                     ensure_ascii=False, indent=2)

# 不知道吃什么推荐工具
@app.tool()
async def what_to_eat(people_count: int):
    """
    不知道吃什么？根据人数直接推荐适合的菜品组合
    
    Args:
        people_count: 用餐人数，1-10之间的整数，会根据人数推荐合适数量的菜品
        
    Returns:
        推荐的菜品组合，包含荤菜和素菜
    """
    import random
    from .utils.recipe_utils import simplify_recipe
    from .types.models import DishRecommendation
    
    recipes = await fetch_recipes()
    if not recipes:
        return "未能获取菜谱数据"
        
    # 根据人数计算荤素菜数量
    vegetable_count = (people_count + 1) // 2
    meat_count = (people_count + 1) // 2 + (people_count + 1) % 2
    
    # 获取所有荤菜
    meat_dishes = [
        recipe for recipe in recipes
        if recipe.category == '荤菜' or recipe.category == '水产'
    ]
    
    # 获取其他可能的菜品（当做素菜）
    vegetable_dishes = [
        recipe for recipe in recipes
        if recipe.category not in ['荤菜', '水产', '早餐', '主食']
    ]
    
    # 特别处理：如果人数超过8人，增加鱼类荤菜
    recommended_dishes = []
    fish_dish = None
    
    if people_count > 8:
        fish_dishes = [recipe for recipe in recipes if recipe.category == '水产']
        if fish_dishes:
            fish_dish = random.choice(fish_dishes)
            recommended_dishes.append(fish_dish)
    
    # 按照不同肉类的优先级选择荤菜
    meat_types = ['猪肉', '鸡肉', '牛肉', '羊肉', '鸭肉', '鱼肉']
    selected_meat_dishes = []
    
    # 需要选择的荤菜数量
    remaining_meat_count = meat_count - (1 if fish_dish else 0)
    
    # 尝试按照肉类优先级选择荤菜
    for meat_type in meat_types:
        if len(selected_meat_dishes) >= remaining_meat_count:
            break
        
        meat_type_options = [
            dish for dish in meat_dishes
            if any(
                meat_type.lower() in (ingredient.name or "").lower()
                for ingredient in dish.ingredients
            )
        ]
        
        if meat_type_options:
            # 随机选择一道这种肉类的菜
            selected = random.choice(meat_type_options)
            selected_meat_dishes.append(selected)
            # 从可选列表中移除，避免重复选择
            meat_dishes = [dish for dish in meat_dishes if dish.id != selected.id]
    
    # 如果通过肉类筛选的荤菜不够，随机选择剩余的
    while len(selected_meat_dishes) < remaining_meat_count and meat_dishes:
        random_dish = random.choice(meat_dishes)
        selected_meat_dishes.append(random_dish)
        meat_dishes.remove(random_dish)
    
    # 随机选择素菜
    selected_vegetable_dishes = []
    while len(selected_vegetable_dishes) < vegetable_count and vegetable_dishes:
        random_dish = random.choice(vegetable_dishes)
        selected_vegetable_dishes.append(random_dish)
        vegetable_dishes.remove(random_dish)
    
    # 合并推荐菜单
    recommended_dishes.extend(selected_meat_dishes)
    recommended_dishes.extend(selected_vegetable_dishes)
    
    # 构建推荐结果
    dish_recommendation = DishRecommendation(
        people_count=people_count,
        meat_dish_count=len(selected_meat_dishes) + (1 if fish_dish else 0),
        vegetable_dish_count=len(selected_vegetable_dishes),
        dishes=[simplify_recipe(dish) for dish in recommended_dishes],
        message=f"为{people_count}人推荐的菜品，包含{len(selected_meat_dishes) + (1 if fish_dish else 0)}个荤菜和{len(selected_vegetable_dishes)}个素菜。"
    )
    
    # 返回JSON字符串
    import json
    return json.dumps(dish_recommendation.model_dump(), ensure_ascii=False, indent=2)

# 推荐膳食计划工具
@app.tool()
async def recommend_meals(people_count: int, allergies: list = None, avoid_items: list = None):
    """
    根据用户的忌口、过敏原、人数智能推荐菜谱，创建一周的膳食计划以及大致的购物清单
    
    Args:
        people_count: 用餐人数，1-10之间的整数
        allergies: 过敏原列表，如['大蒜', '虾']
        avoid_items: 忌口食材列表，如['葱', '姜']
        
    Returns:
        一周的膳食计划以及大致的购物清单
    """
    import random
    import json
    from .utils.recipe_utils import (
        simplify_recipe,
        process_recipe_ingredients,
        categorize_ingredients
    )
    from .types.models import MealPlan, DayPlan
    
    if allergies is None:
        allergies = []
    if avoid_items is None:
        avoid_items = []

    # 统一清洗关键字，避免大小写/空白造成匹配遗漏
    allergies = [str(item).strip().lower() for item in allergies if str(item).strip()]
    avoid_items = [str(item).strip().lower() for item in avoid_items if str(item).strip()]
    
    recipes = await fetch_recipes()
    if not recipes:
        return "未能获取菜谱数据"
    
    def contains_blocked_keyword(recipe) -> bool:
        name_text = (recipe.name or "").lower()

        for keyword in allergies:
            if keyword in name_text:
                return True
        for keyword in avoid_items:
            if keyword in name_text:
                return True

        for ingredient in recipe.ingredients:
            ingredient_name = (ingredient.name or "").lower()
            if any(keyword in ingredient_name for keyword in allergies):
                return True
            if any(keyword in ingredient_name for keyword in avoid_items):
                return True
        return False

    # 过滤掉含有忌口和过敏原的菜谱
    filtered_recipes = [recipe for recipe in recipes if not contains_blocked_keyword(recipe)]

    # 如果过滤后无菜谱，提前返回明确提示
    if not filtered_recipes:
        return "筛选后无可用菜谱，请减少过敏原/忌口条件后重试"

    # 将菜谱按分类分组（保留全部分类，避免候选过窄）
    recipes_by_category = {}
    for recipe in filtered_recipes:
        recipes_by_category.setdefault(recipe.category, []).append(recipe)

    # 为不同餐次定义优先分类和后备分类
    breakfast_categories = ['早餐', '主食']
    lunch_categories = ['荤菜', '水产', '主食', '素菜', '汤羹', '甜品']
    dinner_categories = ['水产', '荤菜', '主食', '素菜', '汤羹', '甜品']
    
    # 创建每周膳食计划
    meal_plan = MealPlan()
    
    # 用于跟踪已经选择的菜谱，以便后续处理食材信息
    selected_recipes = []
    
    def pick_recipe(category_order: list):
        # 优先按顺序命中分类
        for category in category_order:
            candidates = recipes_by_category.get(category, [])
            if candidates:
                index = random.randrange(len(candidates))
                chosen = candidates.pop(index)
                selected_recipes.append(chosen)
                return simplify_recipe(chosen)

        # 兜底：从任意剩余分类中选一道，保证尽量不空位
        non_empty_categories = [cat for cat, items in recipes_by_category.items() if items]
        if non_empty_categories:
            fallback_category = random.choice(non_empty_categories)
            candidates = recipes_by_category[fallback_category]
            index = random.randrange(len(candidates))
            chosen = candidates.pop(index)
            selected_recipes.append(chosen)
            return simplify_recipe(chosen)
        return None

    weekday_names = ['周一', '周二', '周三', '周四', '周五']
    weekend_names = ['周六', '周日']

    for day_name in weekday_names:
        day_plan = DayPlan(day=day_name, breakfast=[], lunch=[], dinner=[])

        breakfast_count = max(1, (people_count + 4) // 5)
        meal_count = max(2, (people_count + 2) // 3)

        for _ in range(breakfast_count):
            recipe = pick_recipe(breakfast_categories)
            if recipe:
                day_plan.breakfast.append(recipe)

        for _ in range(meal_count):
            recipe = pick_recipe(lunch_categories)
            if recipe:
                day_plan.lunch.append(recipe)

        for _ in range(meal_count):
            recipe = pick_recipe(dinner_categories)
            if recipe:
                day_plan.dinner.append(recipe)

        meal_plan.weekdays.append(day_plan)

    for day_name in weekend_names:
        day_plan = DayPlan(day=day_name, breakfast=[], lunch=[], dinner=[])

        breakfast_count = max(2, (people_count + 2) // 3)
        weekday_meal_count = max(2, (people_count + 2) // 3)
        weekend_extra = 1 if people_count <= 4 else 2
        meal_count = weekday_meal_count + weekend_extra

        for _ in range(breakfast_count):
            recipe = pick_recipe(breakfast_categories)
            if recipe:
                day_plan.breakfast.append(recipe)

        for _ in range(meal_count):
            recipe = pick_recipe(lunch_categories)
            if recipe:
                day_plan.lunch.append(recipe)

        for _ in range(meal_count):
            recipe = pick_recipe(dinner_categories)
            if recipe:
                day_plan.dinner.append(recipe)

        meal_plan.weekend.append(day_plan)

    # 统计食材清单
    ingredient_map = {}
    for recipe in selected_recipes:
        process_recipe_ingredients(recipe, ingredient_map)

    meal_plan.grocery_list.ingredients = list(ingredient_map.values())
    categorize_ingredients(
        meal_plan.grocery_list.ingredients,
        meal_plan.grocery_list.shopping_plan
    )

    return json.dumps(meal_plan.model_dump(), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    try:
        app.run(transport='sse')
    except KeyboardInterrupt:
        # Normal manual stop (Ctrl+C) should exit quietly.
        pass
