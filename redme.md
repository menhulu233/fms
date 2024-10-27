创建mobs的语句
```sql
drop schema if exists fms;
create schema fms;
use fms;

CREATE TABLE paddocks (
	id int NOT NULL AUTO_INCREMENT,
	name varchar(50) NOT NULL,
	area float(2) not null,
    dm_per_ha float(2) not null,
	total_dm float(2) default null,
	PRIMARY KEY (id)
);
```
mobs与paddocks关系
```sql
CONSTRAINT fk_paddock
	FOREIGN KEY (paddock_id)
	REFERENCES paddocks(id)
	ON DELETE NO ACTION
	ON UPDATE NO ACTION
```

farms表
```sql
CREATE TABLE farms (
    farm_id INT AUTO_INCREMENT,  -- 自动递增的唯一农场ID
    farm_name VARCHAR(255) NOT NULL,  -- 农场名称，不能为空
    description TEXT,  -- 可选的简短描述
    owner_name VARCHAR(255),  -- 所有的姓名
    PRIMARY KEY (farm_id)  -- 设置主键为 farm_id
);
```
插入的例子
```sql
-- 插入示例农场数据
INSERT INTO farms (farm_name, description, owner_name) VALUES 
('Green Acres Farm', 'A beautiful farm with lush green fields and diverse crops.', 'John Doe');
```
 为了整合新的 `farms` 表，你需要对其他表进行哪些更改？（描述这些更改，不需要 SQL 脚本。）
需要在 paddocks 表中增加一个外键 farm_id，指向 farms 表的 farm_id。
