from flask import Flask, request, render_template, redirect, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)

# Set the secret key from an environment variable
app.secret_key = 'jonhan2003'


# Define the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home route
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/add_new_recipe', methods=['GET', 'POST'])
def add_new_recipe():
    if request.method == 'POST':
        # Handle form submission to add new recipe
        name = request.form['name']
        quantity = request.form['quantity']
        price = request.form['price']
        category = request.form['category']
        unit = request.form['unit']

        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Now 'filename' contains the name of the saved file, you can store it in the database if needed
            else:
                flash('Invalid file type')
                return redirect(request.url)

        # Use a context manager to manage the database connection
        with sqlite3.connect('kitchen.db') as conn:
            c = conn.cursor()

            # Check if a record with the same name already exists
            c.execute("SELECT * FROM recipes WHERE name = ?", (name,))
            existing_recipe = c.fetchone()

            if existing_recipe:
                # Update the existing record
                c.execute("UPDATE recipes SET quantity_in_stock = ?, price = ?, category = ?, unit = ?, image = ? WHERE name = ?",
                          (quantity, price, category, unit, filename, name))
            else:
                # Insert a new record
                c.execute(
                    "INSERT INTO recipes (name, quantity_in_stock, price, category, unit, image) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, quantity, price, category, unit, filename))

            conn.commit()

        return render_template('add_new_recipe.html')
    else:
        return render_template('add_new_recipe.html')


@app.route('/add_new_menu_item', methods=['GET', 'POST'])
def add_new_menu_item():
    if request.method == 'POST':
        # Handle form submission to add new menu item
        name = request.form['name']
        category = request.form['category']  # Get category from form

        # Collect ingredients and quantities
        ingredients = []
        quantities = []
        for i in range(1, 11):
            ingredient = request.form.get(f'ingredient{i}')
            quantity = request.form.get(f'quantity{i}')
            if ingredient and quantity:
                ingredients.append(ingredient)
                quantities.append(float(quantity))

        # Calculate total cost of ingredients
        total_cost = 0
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        for ingredient, quantity in zip(ingredients, quantities):
            c.execute("SELECT price FROM recipes WHERE name=?", (ingredient,))
            ingredient_cost = c.fetchone()[0] * quantity
            total_cost += ingredient_cost
        conn.close()

        # Calculate selling prices
        selling_price_75 = total_cost * 1.75
        selling_price_72 = total_cost * 1.72
        selling_price_70 = total_cost * 1.70
        selling_price_65 = total_cost * 1.65
        selling_price_60 = total_cost * 1.60

        # Add new menu item to the database
        conn = sqlite3.connect('menu.db')
        c = conn.cursor()
        c.execute("INSERT INTO menu (name, category, ingredients, quantities, cost, selling_price_75, selling_price_72, selling_price_70, selling_price_65, selling_price_60) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (name, category, ','.join(ingredients), ','.join(map(str, quantities)), total_cost, selling_price_75, selling_price_72, selling_price_70, selling_price_65, selling_price_60))
        conn.commit()
        conn.close()

        return 'New menu item added successfully!'
    else:
        # Fetch recipe names for dropdown menu
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT name FROM recipes")
        recipe_names = [row[0] for row in c.fetchall()]
        conn.close()

        return render_template('add_new_menu_item.html', recipe_names=recipe_names)

@app.route('/cook', methods=['POST'])
def cook():
    if request.method == 'POST':
        menu_name = request.form['menu_name']
        quantity = request.form['quantity']
        selling_price_percentage = request.form['selling_price_percentage']

        # Retrieve cost per quantity from menu.db
        conn_menu = sqlite3.connect('menu.db')
        cursor_menu = conn_menu.cursor()
        cursor_menu.execute("SELECT cost FROM menu WHERE name=?", (menu_name,))
        row = cursor_menu.fetchone()
        if row:
            cost_per_quantity = row[0] * float(selling_price_percentage) / 100
            conn_menu.close()

            # Save the data into cook.db with current date time
            conn_cook = sqlite3.connect('cook.db')
            cursor_cook = conn_cook.cursor()
            cursor_cook.execute("INSERT INTO cook (date_time, menu_name, quantity, cost_per_quantity) VALUES (?, ?, ?, ?)",
                               (datetime.datetime.now(), menu_name, quantity, cost_per_quantity))
            conn_cook.commit()
            conn_cook.close()

            return "Cooking information saved successfully."
        else:
            return "Error: Menu not found."

@app.route('/add_existing_recipe', methods=['GET', 'POST'])
def add_existing_recipe():
    if request.method == 'POST':
        # Handle adding existing recipe
        name = request.form['name']
        quantity = int(request.form['quantity'])

        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM recipes WHERE name = ?", (name,))
        recipe_exists = c.fetchone()[0] > 0

        if recipe_exists:
            c.execute("SELECT quantity_in_stock FROM recipes WHERE name = ?", (name,))
            current_quantity = c.fetchone()[0]
            new_quantity = current_quantity + quantity
            c.execute("UPDATE recipes SET quantity_in_stock = ? WHERE name = ?", (new_quantity, name))
            conn.commit()
            conn.close()
            return 'Recipe quantity updated successfully!'
        else:
            conn.close()
            return 'Error: Recipe not found!'
    else:
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT name FROM recipes")
        recipe_names = c.fetchall()
        conn.close()
        return render_template('add_existing_recipe.html', recipe_names=recipe_names)

# View database route
@app.route('/view_database', methods=['GET', 'POST'])
def view_database():
    conn = sqlite3.connect('kitchen.db')
    c = conn.cursor()

    if request.method == 'POST':
        selected_category = request.form['category']
        c.execute("SELECT * FROM recipes WHERE category=?", (selected_category,))
        recipes = c.fetchall()
    else:
        c.execute("SELECT * FROM recipes")
        recipes = c.fetchall()

    categories = c.execute("SELECT DISTINCT category FROM recipes").fetchall()

    conn.close()
    return render_template('view_database.html', recipes=recipes, categories=categories)

# Delete recipe route
@app.route('/delete_recipe/<name>', methods=['POST'])
def delete_recipe(name):
    conn = sqlite3.connect('kitchen.db')
    c = conn.cursor()
    c.execute("DELETE FROM recipes WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return 'Recipe deleted successfully!'

# Function to fetch data from menu database
def get_menu_data():
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM menu")
    menu_data = c.fetchall()
    conn.close()
    return menu_data

# View menu database route
@app.route('/view_menu_database')
def view_menu_database():
    menu_data = get_menu_data()
    return render_template('view_menu_database.html', recipes=menu_data)
@app.route('/view_cook_data')
def view_cook_data():
    conn = sqlite3.connect('cook.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cook")
    data = cursor.fetchall()
    conn.close()
    return render_template('view_cook_data.html', data=data)


def get_categoriess():
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM menu")
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

def get_menu_itemss(category):
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM menu WHERE category=?", (category,))
    items = c.fetchall()
    conn.close()
    return render_template('menu_table.html', items=items)

def get_menu_item_detailss(id):
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM menu WHERE id=?", (id,))
    item = c.fetchone()
    conn.close()
    return render_template('menu_details.html', item=item)

@app.route('/menu2', methods=['GET', 'POST'])
def menu2():
    categories = get_categoriess()
    return render_template('menu2.html', categories=categories)

@app.route('/get_menu_items', methods=['GET'])
def get_menu():
    category = request.args.get('category')
    items_html = get_menu_itemss(category)
    return items_html

@app.route('/get_menu_item_details', methods=['GET'])
def get_menu_item_details_route():
    id = request.args.get('id')
    details_html = get_menu_item_detailss(id)
    return details_html

from flask import Flask, request, render_template, redirect, flash, send_from_directory
import sqlite3
import datetime  # Import datetime module
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

# Home route
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Define the upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_new_recipe', methods=['GET', 'POST'])
def add_new_recipe():
    if request.method == 'POST':
        # Handle form submission to add new recipe
        name = request.form['name']
        quantity = request.form['quantity']
        price = request.form['price']
        category = request.form['category']
        unit = request.form['unit']

        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                # Now 'filename' contains the name of the saved file, you can store it in the database if needed
            else:
                flash('Invalid file type')
                return redirect(request.url)

        # Use a context manager to manage the database connection
        with sqlite3.connect('kitchen.db') as conn:
            c = conn.cursor()

            # Check if a record with the same name already exists
            c.execute("SELECT * FROM recipes WHERE name = ?", (name,))
            existing_recipe = c.fetchone()

            if existing_recipe:
                # Update the existing record
                c.execute("UPDATE recipes SET quantity_in_stock = ?, price = ?, category = ?, unit = ?, image = ? WHERE name = ?",
                          (quantity, price, category, unit, filename, name))
            else:
                # Insert a new record
                c.execute(
                    "INSERT INTO recipes (name, quantity_in_stock, price, category, unit, image) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, quantity, price, category, unit, filename))

            conn.commit()

        return 'New recipe added successfully!'
    else:
        return render_template('add_new_recipe.html')

@app.route('/add_new_menu_item', methods=['GET', 'POST'])
def add_new_menu_item():
    if request.method == 'POST':
        # Handle form submission to add new menu item
        name = request.form['name']
        category = request.form['category']  # Get category from form

        # Collect ingredients and quantities
        ingredients = []
        quantities = []
        for i in range(1, 11):
            ingredient = request.form.get(f'ingredient{i}')
            quantity = request.form.get(f'quantity{i}')
            if ingredient and quantity:
                ingredients.append(ingredient)
                quantities.append(float(quantity))

        # Calculate total cost of ingredients
        total_cost = 0
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        for ingredient, quantity in zip(ingredients, quantities):
            c.execute("SELECT price FROM recipes WHERE name=?", (ingredient,))
            ingredient_cost = c.fetchone()[0] * quantity
            total_cost += ingredient_cost
        conn.close()

        # Calculate selling prices
        selling_price_75 = total_cost * 1.75
        selling_price_72 = total_cost * 1.72
        selling_price_70 = total_cost * 1.70
        selling_price_65 = total_cost * 1.65
        selling_price_60 = total_cost * 1.60

        # Add new menu item to the database
        conn = sqlite3.connect('menu.db')
        c = conn.cursor()
        c.execute("INSERT INTO menu (name, category, ingredients, quantities, cost, selling_price_75, selling_price_72, selling_price_70, selling_price_65, selling_price_60) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (name, category, ','.join(ingredients), ','.join(map(str, quantities)), total_cost, selling_price_75, selling_price_72, selling_price_70, selling_price_65, selling_price_60))
        conn.commit()
        conn.close()

        return 'New menu item added successfully!'
    else:
        # Fetch recipe names for dropdown menu
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT name FROM recipes")
        recipe_names = [row[0] for row in c.fetchall()]
        conn.close()

        return render_template('add_new_menu_item.html', recipe_names=recipe_names)

# Function to fetch menu items from the database
def get_menu_items():
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM menu")
    menu_items = cursor.fetchall()
    conn.close()
    return menu_items

# Function to fetch menu information based on selected item
def get_menu_info(menu_name):
    conn = sqlite3.connect('menu.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE name=?", (menu_name,))
    menu_info = cursor.fetchone()
    conn.close()
    return menu_info

@app.route('/menu', methods=['GET', 'POST'])
def menu():
    menu_info = None
    cost_info = None  # Initialize cost_info
    if request.method == 'POST':
        selected_menu = request.form['menu']
        menu_info = get_menu_info(selected_menu)
        # Check if menu_info is not None
        if menu_info:
            # Split the ingredients, quantities, and cost into lists
            ingredients = menu_info[2].split(',')
            quantities = menu_info[3].split(',')
            cost = menu_info[4]  # Get cost directly from the database
            # Combine the ingredients and quantities into a list of tuples
            menu_info = list(zip(ingredients, quantities))
            cost_info = {'cost': cost, 'selling_price': cost * 1.33}  # Calculate selling price
    menu_items = get_menu_items()
    return render_template('hi.html', menu_info=menu_info, menu_items=menu_items, cost_info=cost_info)







def calculate_ingredients(menu_name, quantities):
    total_ingredients_needed = {}
    try:
        # Connect to the menu database
        conn = sqlite3.connect('menu.db')
        cursor = conn.cursor()

        # Retrieve ingredients and quantities for the selected menu
        cursor.execute("SELECT ingredients, quantities FROM menu WHERE name=?", (menu_name,))
        menu_data = cursor.fetchone()

        if menu_data:
            ingredients_str, quantities_str = menu_data
            ingredients = ingredients_str.split(',')
            quantities_per_dish = [float(q) for q in quantities_str.split(',')]
            for ingredient, quantity_per_dish, quantity in zip(ingredients, quantities_per_dish, quantities):
                total_ingredients_needed[ingredient] = float(quantity) * quantity_per_dish

    except sqlite3.Error as e:
        print("Error fetching data from menu database:", e)

    finally:
        if conn:
            conn.close()

    return total_ingredients_needed

def update_stock(total_ingredients_needed):
    try:
        # Connect to the kitchen database
        conn = sqlite3.connect('kitchen.db')
        cursor = conn.cursor()

        for ingredient, quantity_needed in total_ingredients_needed.items():
            # Fetch current quantity in stock
            cursor.execute("SELECT quantity_in_stock FROM recipes WHERE name=?", (ingredient,))
            current_stock = cursor.fetchone()[0]

            # Update stock
            new_stock = current_stock - quantity_needed
            cursor.execute("UPDATE recipes SET quantity_in_stock=? WHERE name=?", (new_stock, ingredient))
            conn.commit()

    except sqlite3.Error as e:
        print("Error updating stock in kitchen database:", e)

    finally:
        if conn:
            conn.close()

@app.route('/add_existing_recipe', methods=['GET', 'POST'])
def add_existing_recipe():
    if request.method == 'POST':
        # Handle adding existing recipe
        name = request.form['name']
        quantity = int(request.form['quantity'])

        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM recipes WHERE name = ?", (name,))
        recipe_exists = c.fetchone()[0] > 0

        if recipe_exists:
            c.execute("SELECT quantity_in_stock FROM recipes WHERE name = ?", (name,))
            current_quantity = c.fetchone()[0]
            new_quantity = current_quantity + quantity
            c.execute("UPDATE recipes SET quantity_in_stock = ? WHERE name = ?", (new_quantity, name))
            conn.commit()
            conn.close()
            return 'Recipe quantity updated successfully!'
        else:
            conn.close()
            return 'Error: Recipe not found!'
    else:
        conn = sqlite3.connect('kitchen.db')
        c = conn.cursor()
        c.execute("SELECT name FROM recipes")
        recipe_names = c.fetchall()
        conn.close()
        return render_template('add_existing_recipe.html', recipe_names=recipe_names)

# View database route
@app.route('/view_database', methods=['GET', 'POST'])
def view_database():
    conn = sqlite3.connect('kitchen.db')
    c = conn.cursor()

    if request.method == 'POST':
        selected_category = request.form['category']
        c.execute("SELECT * FROM recipes WHERE category=?", (selected_category,))
        recipes = c.fetchall()
    else:
        c.execute("SELECT * FROM recipes")
        recipes = c.fetchall()

    categories = c.execute("SELECT DISTINCT category FROM recipes").fetchall()

    conn.close()
    return render_template('view_database.html', recipes=recipes, categories=categories)

# Delete recipe route
@app.route('/delete_recipe/<name>', methods=['POST'])
def delete_recipe(name):
    conn = sqlite3.connect('kitchen.db')
    c = conn.cursor()
    c.execute("DELETE FROM recipes WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return 'Recipe deleted successfully!'

# Function to fetch data from menu database
def get_menu_data():
    conn = sqlite3.connect('menu.db')
    c = conn.cursor()
    c.execute("SELECT * FROM menu")
    menu_data = c.fetchall()
    conn.close()
    return menu_data

# View menu database route
@app.route('/view_menu_database')
def view_menu_database():
    menu_data = get_menu_data()
    return render_template('view_menu_database.html', recipes=menu_data)
@app.route('/view_cook_data')
def view_cook_data():
    conn = sqlite3.connect('cook.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cook")
    data = cursor.fetchall()
    conn.close()
    return render_template('view_cook_data.html', data=data)

def get_categorie():
    try:
        conn = sqlite3.connect('menu.db')
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM menu")
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        return categories
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return []

def get_menu_item(category):
    try:
        conn = sqlite3.connect('menu.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM menu WHERE category=?", (category,))
        menu_items = [row[0] for row in cursor.fetchall()]
        conn.close()
        return menu_items
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return []

def update_kitchen_stock(menu_name, quantity):
    try:
        # Connect to the databases
        menu_conn = sqlite3.connect('menu.db')
        kitchen_conn = sqlite3.connect('kitchen.db')

        # Retrieve recipe information
        cursor = menu_conn.cursor()
        cursor.execute("SELECT * FROM menu WHERE name=?", (menu_name,))
        recipe_data = cursor.fetchone()

        if recipe_data is None:
            return "Recipe not found"

        # Split ingredients and quantities
        ingredients = recipe_data[2].split(',')
        ingredient_quantities = recipe_data[3].split(',')

        # Update kitchen stock
        kitchen_cursor = kitchen_conn.cursor()
        for ingredient, ingredient_quantity in zip(ingredients, ingredient_quantities):
            ingredient_quantity = float(ingredient_quantity) * quantity
            kitchen_cursor.execute("UPDATE recipes SET quantity_in_stock = quantity_in_stock - ? WHERE name=?",
                                   (ingredient_quantity, ingredient,))
            kitchen_conn.commit()

        return "Stock updated successfully"
    except sqlite3.Error as e:
        return f"SQLite error: {e}"


@app.route('/update_stock', methods=['GET', 'POST'])
def update_stock():
    if request.method == 'POST':
        selected_menu = request.form['menu_name']
        quantity = int(request.form['quantity'])
        result = update_kitchen_stock(selected_menu, quantity)
        return result
    else:
        categories = get_categorie()
        return render_template('update_stock.html', categories=categories)

@app.route('/get_menu_item', methods=['POST'])
def get_menu_items():
    selected_category = request.form['selected_category']
    menu_items = get_menu_item(selected_category)
    return jsonify(menu_items=menu_items, selected_category=selected_category)

if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'

    app.run(debug=True, port=5001)
