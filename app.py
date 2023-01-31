from flask import Flask,request
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
import covasim as cv
import sciris as sc
import os

app = Flask(__name__)
# 项目配置，类似于热刷新模式
app.debug = True
# 跨域请求
cors = CORS(app)
# 数据库配置
# MySQL 所在的主机名
HOSTNAME = "localhost"
# MySQL 监听的端口号，默3306
PORT = 3306
# 连接MySQL的用户名
USERNAME = "root"
# 连接MySQL的密码
PASSWORD = "123456"
# MySQL上创建的数据库名
DATABASE = "test"
# 在app中存入数据库连接地址
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{USERNAME}:{PASSWORD}@{HOSTNAME}:{PORT}/{DATABASE}?charset=utf8"
# 创建连接好的数据库对象
db = SQLAlchemy(app)

# 连接成功与否测试
# with app. app_context():
#     with db.engine.connect() as conn:
#         rs = conn. execute("select 1")
#         print(rs. fetchone()) # (1,)

# migrate 实现数据库创建的同步
migrate = Migrate(app,db)
# 相关同步指令
# flask db init 1次初始化
# flask db migrate 识别orm的改变迁移生成
# flask db upgrade 更新改变到数据库

# 创建数据表，需要继承自db.Model
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
# 定义访问数据的接口
class UserApi(MethodView):
    def get(self):
        users = User.query.all()
        res = [
            {
                'password': user.password,
                'username': user.username,
                'email': user.email,
            }for user in users
        ]
        return {
            'code': 200,
            'data': res

        }
    def post(self):
        # 将请求转为json
        form = request.json
        user = User()
        user.username = form.get("username")
        user.password = form.get("password")
        user.email = form.get("email")
        db.session.add(user)
        db.session.commit()
        return {
            'code': 200,
            'data': {
                'message': '用户成功添加'
            },
        }



# 注册视图函数
user_view = UserApi.as_view("user_api")
app.add_url_rule('/getUsers', view_func=user_view,methods=['GET'])
app.add_url_rule('/addUser', view_func=user_view,methods=['POST'])

# 自定义指令初始化数据库数据
@app.cli.command()
def create():
    db.drop_all()
    db.create_all()
    user1 = User(username="Gina",password="123",email="123@163.com")
    user2 = User(username="Tina", password="123", email="123@163.com")
    db.session.add(user1)
    db.session.add(user2)
    db.session.commit()
# covasim 方法使用
# 关键的三组参数字典，留给调试的时候使用
# sim_pars = {
#     'start_day': '2022-01-01',
#     'end_day': '2022-01-31',
#     'pop_infected': 10,
#     'pop_size': 5000,
#     'pop_type': 'hybrid',
#     'contacts': {'h': 3, 'c': 36, 's': 50, 'w': 20},
#     'variant_start_day': '2022-01-04',
#     'n_import': 3
#
# }
epi_pars = {
    'rel_beta': 0.0208178 / 0.016,
    'beta': 0.0208178

}
int_pars = {
    'mask_wearing': [
        {
            'days': ['2022-01-03', '2022-04-05'],
            'layer': 'h',
            'value': [1.0, 0.9]
        }
    ]
}
# 根据表单传入的参数创建sim
def createSim(sim_pars,epi_pars,int_pars):

    # 将传来的参数用于sim模拟的参数解析出来，传给sim

    pop_infected = sim_pars['pop_infected']

    start_day = sim_pars['start_day']
    end_day = sim_pars['end_day']


    pop_size = sim_pars['pop_size']

    pop_type = sim_pars['pop_type']

    contacts = sim_pars['contacts']
    pars = sc.objdict(

        pop_size=pop_size,
        pop_infected=pop_infected,
        pop_type=pop_type,
        start_day=start_day,
        end_day=end_day,
        contacts=contacts,
        verbose=0,
    )

    sim = cv.Sim(pars=pars, location = 'China')

    # 设定相对流行病学参数

    # 用户选择模式设定病毒参数
    regions = {
        # 'n_imports': {
        #     'Default': 0,
        #     'Optimistic': 0,
        #     'Pessimistic': 10,
        # },
        'beta': {
            'Default': 0.015,
            'Optimistic': 0.010,
            'Pessimistic': 0.02,
        },
        'rel_symp_prob': {
            'Default': 1.0,
            'Optimistic': 1.2,
            'Pessimistic': 0.5,
        },
        'rel_severe_prob': {
            'Default': 1.0,
            'Optimistic': 0.3,
            'Pessimistic': 3.0,
        },
        'rel_crit_prob': {
            'Default': 1.0,
            'Optimistic': 0.7,
            'Pessimistic': 5.0,
        },
        'rel_death_prob': {
            'Default': 1.0,
            'Optimistic': 0.5,
            'Pessimistic': 2.0,
        },
    }

    # 用户选择了直接设定相对传播数值
    if epi_pars['isUseful']:
        sim.pars['beta'] = epi_pars['beta']
        sim.pars['rel_symp_prob'] = epi_pars['symp']
        sim.pars['rel_severe_prob'] = epi_pars['severe']
        sim.pars['rel_crit_prob'] = epi_pars['crit']
        sim.pars['rel_death_prob'] = epi_pars['death']
    else:
        # 用户选择给悲观或乐观模式赋值
        if sim_pars['epi_degree'] == 'optimistic':
            for key, value in regions.items():
                if key == 'beta':
                    sim.pars[key] = value['Optimistic']
                else:
                    sim.pars[key] = sim.pars[key]*value['Optimistic']
        elif sim_pars['epi_degree'] == 'pessimistic':
            for key, value in regions.items():
                if key == 'beta':
                    sim.pars[key] = value['Pessimistic']
                else:
                    sim.pars[key] = sim.pars[key] * value['Pessimistic']
        elif sim_pars['epi_degree'] == 'default':
            sim.pars['beta'] = regions['beta']['Default']
    # elif epi_pars['rel_beta']:
    #     sim.pars['rel_beta'] = epi_pars['rel_beta']

    # if sim_pars['n_import'] != 0:
    #     # 设置omicron病毒引入
    #     # Adding Omicron,设置相对于初始病毒的传播率
    #     omicron = cv.variant('p1', days=sim.day(sim_pars['variant_start_day']), n_imports=sim_pars['n_import'])
    #     omicron.p['rel_beta'] = epi_pars['rel_beta']#0.0208178 / 0.016
    #     sim['variants'] += [omicron]


    # 添加防疫措施
    interventions = []
    if sim_pars['interv_degree'] == 'positive':
        interventions.append(cv.change_beta(days=[start_day], changes=[0.8], layers='c'))
        interventions.append(cv.change_beta(days=[start_day], changes=[0.8], layers='s'))
        interventions.append(cv.change_beta(days=[start_day], changes=[0.8], layers='w'))

    elif int_pars:
        if int_pars['mask_wearing']:
            for item in int_pars['mask_wearing']:
                interv = cv.change_beta(days=item['days'], changes=item['value'], layers=item['layer'])
                interventions.append(interv)
    sim.update_pars(interventions=interventions)
    for intervention in sim['interventions']:
         intervention.do_plot = False

    return sim

#@app.route('/sim_res') # 返回模拟的json结果,留给调试的时候使用
# def getSimRes():
#     sim = createSim(sim_pars=sim_pars,epi_pars=epi_pars,int_pars=int_pars)
#
#     sim.run()
#     print(sim.results['cum_infections'])
#     return{
#         'code': 200,
#         'data': {
#             'cumData': [
#                 {
#                     'name': 'cum_infection',
#                     'color': sim.results['cum_infections'].color,
#                     'values': sim.results['cum_infections'].values.tolist()
#                 },
#                 {
#
#                         'name': 'cum_severe',
#                         'color': sim.results['cum_severe'].color,
#                         'values': sim.results['cum_severe'].values.tolist()
#
#                 },
#                 {
#
#                     'name': 'cum_critical',
#                     'color': sim.results['cum_critical'].color,
#                     'values': sim.results['cum_critical'].values.tolist()
#
#                 },
#                 {
#
#                     'name': 'cum_deaths',
#                     'color': sim.results['cum_deaths'].color,
#                     'values': sim.results['cum_deaths'].values.tolist()
#
#                 }
#             ],
#             'newData': [
#                 {
#                     'name': 'new_infection',
#                     'color': sim.results['new_infections'].color,
#                     'values': sim.results['new_infections'].values.tolist()
#                 },
#                 {
#
#                     'name': 'new_severe',
#                     'color': sim.results['new_severe'].color,
#                     'values': sim.results['new_severe'].values.tolist()
#
#                 },
#                 {
#
#                     'name': 'new_critical',
#                     'color': sim.results['new_critical'].color,
#                     'values': sim.results['new_critical'].values.tolist()
#
#                 },
#                 {
#
#                     'name': 'new_deaths',
#                     'color': sim.results['new_deaths'].color,
#                     'values': sim.results['new_deaths'].values.tolist()
#
#                 }
#             ],
#             'date': sim.results.date.tolist()
#         }
#     }


@app.route('/upload',methods=['POST'])
def handleUpload():
    file = request.files.get("file")
    if file is None:  # 表示没有发送文件
        return {
            'msg': "文件上传失败"
        }
    # 修改为固定的名字方便网络读取
    file_name = 'agentsInfo.xlsx'
    file.save(os.path.dirname(__file__) + '/file/' + file_name)  # 保存文件


    return {
        'code': 200,
        'data': '文件上传成功'
    }
@app.route('/run_sim',methods=['POST']) # 接收参数，运行run，并且返回模拟的结果
def runSim():
    form = request.json
    sim_pars = form.get('sim_pars')
    epi_pars = form.get('epi_pars')
    sim = createSim(sim_pars=sim_pars, epi_pars=epi_pars, int_pars=int_pars)
    sim.run()
    return {
        'code': 200,
        'data': {
            'cumData': [
                {
                    'name': 'cum_infection',
                    'color': sim.results['cum_infections'].color,
                    'values': sim.results['cum_infections'].values.tolist()
                },
                {
                    'name': 'cum_recoveries',
                    'color': sim.results['cum_recoveries'].color,
                    'values': sim.results['cum_recoveries'].values.tolist()
                },
                {

                    'name': 'cum_severe',
                    'color': sim.results['cum_severe'].color,
                    'values': sim.results['cum_severe'].values.tolist()

                },
                {

                    'name': 'cum_critical',
                    'color': sim.results['cum_critical'].color,
                    'values': sim.results['cum_critical'].values.tolist()

                },
                {

                    'name': 'cum_deaths',
                    'color': sim.results['cum_deaths'].color,
                    'values': sim.results['cum_deaths'].values.tolist()

                }
            ],
            'newData': [
                {
                    'name': 'new_infection',
                    'color': sim.results['new_infections'].color,
                    'values': sim.results['new_infections'].values.tolist()
                },
                {
                    'name': 'new_recoveries',
                    'color': sim.results['new_recoveries'].color,
                    'values': sim.results['new_recoveries'].values.tolist()
                },
                {

                    'name': 'new_severe',
                    'color': sim.results['new_severe'].color,
                    'values': sim.results['new_severe'].values.tolist()

                },
                {

                    'name': 'new_critical',
                    'color': sim.results['new_critical'].color,
                    'values': sim.results['new_critical'].values.tolist()

                },
                {

                    'name': 'new_deaths',
                    'color': sim.results['new_deaths'].color,
                    'values': sim.results['new_deaths'].values.tolist()

                }
            ],
            'date': sim.results.date.tolist(),
            'panelData': {
                'cum_infections': sim.results['cum_infections'][-1],
                'cum_severe': sim.results['cum_severe'][-1],
                'cum_critical': sim.results['cum_critical'][-1],
                'cum_recoveries': sim.results['cum_recoveries'][-1],
                'cum_deaths': sim.results['cum_deaths'][-1],
            },


        }
    }

@app.route('/')
def hello():
    return 'Hello, World'


if __name__ == '__main__':
    app.run()
