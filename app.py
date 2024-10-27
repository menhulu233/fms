from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from datetime import date, datetime, timedelta
import mysql.connector
import connect

app = Flask(__name__, static_folder='static')
app.secret_key = 'COMP636 S2'
start_date = datetime(2024, 10, 29)

# 这里是两个单位
# pasture_growth_rate：牧草每天每公顷干物质的生长率。
# stock_consumption_rate：每只牲畜每天消耗的牧草干物质量。
pasture_growth_rate = 65  # kg DM/ha/day
stock_consumption_rate = 14  # kg DM/animal/day

db_connection = None


def getCursor():
    """Gets a new dictionary cursor for the database.
    If necessary, a new database connection is created here and used for all
    subsequent to getCursor()."""
    global db_connection

    if db_connection is None or not db_connection.is_connected():
        db_connection = mysql.connector.connect(user=connect.dbuser, \
                                                password=connect.dbpass, host=connect.dbhost,
                                                database=connect.dbname, autocommit=True)

    cursor = db_connection.cursor(buffered=False)  # returns a list
    # cursor = db_connection.cursor(dictionary=True, buffered=False)

    return cursor


@app.route("/")
def home():
    if 'curr_date' not in session:
        session.update({'curr_date': start_date})
    return render_template("home.html")


@app.route("/clear-date")
def clear_date():
    """Clear session['curr_date']. Removes 'curr_date' from session dictionary."""
    session.pop('curr_date')
    return redirect(url_for('paddocks'))


@app.route("/reset-date")
def reset_date():
    """Reset session['curr_date'] to the project start_date value."""
    session.update({'curr_date': start_date})
    return redirect(url_for('paddocks'))


def execute_sql(qstr):
    connection = getCursor()
    connection.execute(qstr)
    result = connection.fetchall()
    result = [list(r) for r in result]
    return result

def days_between_dates(date1: str) -> int:
    # 将字符串转换为日期对象
    date_format = "%Y-%m-%d"
    d1 = datetime.strptime(date1, date_format)
    # 计算两个日期之间的差异
    d2=session["curr_date"].replace(tzinfo=None)
    delta = abs((d2 - d1).days)
    return delta
@app.route("/mobs")
def mobs():
    """List the mob details (excludes the stock in each mob)."""
    connection = getCursor()
    qstr = "select id, name,paddock_id from mobs;"
    mobs = execute_sql(qstr)
    qstr = "select id, name from paddocks;"
    paddocks = execute_sql(qstr)
    for mob in mobs:
        for paddock in paddocks:
            if mob[2] == paddock[0]:
                mob.append(paddock[1])
    mobs = sorted(mobs, key=lambda x: x[1])
    return render_template("mobs.html", mobs=mobs)


# 这里是展示牧场
@app.route("/paddocks",methods=["GET", "POST"])
def paddocks():
    qstr = '''SELECT 
        p.*,
        m.name,
        COALESCE(COUNT(s.mob_id), 0) AS stock_count
    FROM 
        paddocks p
    JOIN 
        mobs m ON p.id = m.paddock_id
    LEFT JOIN 
        stock s ON s.mob_id = m.id
    GROUP BY 
        p.id, m.id;'''
    paddocks_data = execute_sql(qstr)
    if request.method=="GET":
        pass
    else:
        date = request.form.get("date")
        days=days_between_dates(date)
        for paddock in paddocks_data:
            print(paddock)
            dm,total_dm=get_dm(paddock[4],pasture_growth_rate,stock_consumption_rate,paddock[2],paddock[-1],days)
            paddock[3]=dm
            paddock[4]=round(total_dm,2)
    return render_template("paddocks.html", paddocks_data=paddocks_data)


def get_dm(initial_total_dry_matter,pasture_growth_rate,stock_consumption_rate,area,num_stock,days):
    # 其他参数
    # 当前总干物质
    current_total_dry_matter = initial_total_dry_matter
    pasture_growth = calculate_pasture_growth(area, pasture_growth_rate)*days
    stock_consumption = calculate_stock_consumption(num_stock, stock_consumption_rate)*days
    # 更新总干物质
    current_total_dry_matter = update_total_dry_matter(current_total_dry_matter, pasture_growth, stock_consumption)
    # 重新计算每公顷的干物质（DM/ha）
    dm_per_hectare = calculate_dm_per_hectare(area, current_total_dry_matter)
    return current_total_dry_matter,dm_per_hectare


def calculate_pasture_growth(area, growth_rate):
    return area * growth_rate
    # 计算每天的牧草生长和消耗


def calculate_stock_consumption(num_stock, consumption_rate):
    return num_stock * consumption_rate

def update_total_dry_matter(current_total_dry_matter, pasture_growth, stock_consumption):
    new_total_dry_matter = current_total_dry_matter + pasture_growth - stock_consumption
    return new_total_dry_matter

def calculate_dm_per_hectare(area, total_dry_matter):
    if area > 0:
        return total_dry_matter / area
    else:
        return 0

def calculate_age(birth_date):
    current_date = session.get("curr_date").date()
    year_diff = current_date.year - birth_date.year
    if (current_date.month, current_date.day) < (birth_date.month, birth_date.day):
        year_diff -= 1
    return year_diff


# 这里是具体的动物
@app.route('/stock')
def stock():
    """List stock details."""
    qstr = "SELECT id,name,paddock_id FROM mobs;"
    mobs = execute_sql(qstr)
    qstr = "SELECT id,name FROM paddocks"
    paddocks = execute_sql(qstr)
    qstr = "SELECT mob_id,ROUND(AVG(weight),2) as average_weight FROM stock GROUP BY mob_id;"
    stocks = execute_sql(qstr)
    for mob in mobs:
        for paddock in paddocks:
            if mob[2] == paddock[0]:
                mob.append(paddock[1])
        for stock in stocks:
            if mob[0] == stock[0]:
                mob.append(stock[1])
    mobs = sorted(mobs, key=lambda x: x[1])
    detail_data = []
    for i in range(len(mobs)):
        mob_id = mobs[i][0]
        qstr = f"SELECT id,mob_id,dob,weight FROM stock WHERE mob_id={mob_id}"
        detail_data.extend(execute_sql(qstr))
    for d in detail_data:
        print(d[2])
        d.append(calculate_age(d[2]))
    return render_template("stock.html", mobs=mobs, detail_data=detail_data)


@app.route("/move_mob", methods=["POST", "GET"])
def move_mob():
    if request.method == "GET":
        all_mobs = execute_sql("SELECT * FROM mobs")
        paddock_ids = [mob[2] for mob in all_mobs]
        all_paddocks = execute_sql("SELECT id,name FROM paddocks")
        all_paddocks = [paddock for paddock in all_paddocks if paddock[0] not in paddock_ids]
        return render_template("move_mob.html", all_mobs=all_mobs, all_paddocks=all_paddocks)
    elif request.method == "POST":
        op_mob_id = request.form["op_mob_id"]
        op_paddock_id = request.form["op_paddock_id"]
        if op_paddock_id and op_mob_id:
            currsor = getCursor()
            qstr = f"UPDATE mobs SET paddock_id={op_paddock_id} WHERE id={op_mob_id};"
            currsor.execute(qstr)
            currsor.fetchone()
    return redirect("/")


@app.route("/add_update_paddock", methods=["GET", "POST"])
def add_update_paddock():
    if request.method == "GET":
        paddock_id = request.args.get("paddock_id", "")
        if paddock_id:
            qstr = f"SELECT * FROM paddocks WHERE id={paddock_id};"
            paddocks = execute_sql(qstr)
            paddock = paddocks[0]
        else:
            paddock = None
        return render_template("add_update_paddock.html", paddock=paddock)
    elif request.method == "POST":
        print(request.form)
        id = request.form.get("id", "")
        name = request.form.get("name", "")
        area = request.form.get("area", 0)
        area = float(area)
        dm_per_ha = request.form.get("dm_per_ha", 0)
        dm_per_ha = float(dm_per_ha)
        total_dm = area * dm_per_ha
        print(id)
        if id:
            qstr = f"UPDATE paddocks SET name='{name}',area={area},dm_per_ha={dm_per_ha},total_dm={total_dm} WHERE id={id}"
        else:
            ids = execute_sql("SELECT id FROM paddocks;")
            ids = [id[0] for id in ids]
            id = max(ids) + 1
            qstr = f"INSERT INTO paddocks (id,name, area, dm_per_ha,total_dm) VALUES ({id},'{name}', {area}, {dm_per_ha},{total_dm});"
        cursor = getCursor()
        print(qstr)
        cursor.execute(qstr)
        cursor.fetchone()
        return redirect("/")
    return redirect("/")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8089)
