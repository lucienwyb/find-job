# AI4Science 随便玩玩指南（半小时起步，不设KPI）

> 目标：让你直观感受"用AI解科学问题"酷不酷、是不是你的菜。应用物理本科友好。
> 模式：玩，不写简历不投递不作战计划。做完只记一个字：爽/不爽。

## 为什么选这两个子方向起步

| 子方向 | 为什么对你友好 | 上手难度 | "发现感" |
|------|--------------|---------|---------|
| 蛋白质结构预测(ESMFold) | 物理直觉(折叠=能量最低)=物理问题,ESMFold比AlphaFold快不需数据库 | 半小时 | 高(看蛋白3D结构) |
| 分子性质预测(RDKit+简单ML) | 化学式=数据,物理本科数理基础直接用 | 半小时 | 中(预测分子毒性/溶解度) |
| 材料发现(MatterGen) | 物理/材料门票真有用,但环境装麻烦 | 2-3小时 | 高但门槛高 |
| PDE/科学计算AI(PINN) | 最贴物理本科(偏微分方程),但偏学术 | 1-2小时 | 中(解方程没什么视觉冲击) |

→ 先玩ESMFold(最快有视觉冲击+物理直觉)+RDKit(最简单),不喜欢再换。

## 玩法1：ESMFold 蛋白质结构预测（推荐第一个，20分钟）

### 背景（1分钟看）
蛋白质是氨基酸链,会折叠成3D结构,结构决定功能。预测结构=解一个能量最低的物理问题(诺贝尔奖级)。ESMFold是Meta的模型,输入氨基酸序列输出3D结构,比AlphaFold快且不需序列库对齐。

### 步骤（Google Colab，免费GPU）
1. 打开浏览器 → Google Colab (https://colab.research.google.com)
2. 新建笔记本 → 运行时→更改运行时类型→选GPU(T4免费)
3. 第一个cell装包并加载：
```python
!pip install -q fair-esm
import torch
import esm
# 加载ESMFold模型(首次会下载~3GB,耐心等)
model = esm.pretrained.esmfold_v1()
model = model.eval().cuda()
```
4. 第二个cell预测一个真实蛋白(选一个你熟的,比如某个激酶或p53肿瘤抑制蛋白):
```python
# p53肿瘤抑制蛋白的一段序列
sequence = "MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSSELQS"
output = model.infer_pdb(sequence)
with open("p53.pdb","w") as f: f.write(output)
print("结构已生成 p53.pdb")
```
5. 第三个cell可视化3D结构:
```python
!pip install -q py3Dmol
import py3Dmol
view = py3Dmol.view(query='pdb:p53', width=600, height=400)  # 或本地文件
view.setStyle({'cartoon':{'color':'spectrum'}})
view.show()
```
6. **看那个3D结构转起来——这就是"用AI解了一个物理问题"的瞬间**

### 玩完问自己
- 看到蛋白3D结构那一刻,是"卧槽好酷想多搞"还是"就这"?
- 想不想换个序列再跑、改参数看结构变化、读ESMFold原理?
- 还是觉得"离我太远,不知道在解决谁的题"?

## 玩法2：RDKit 分子性质预测（15分钟，若玩法1还不过瘾）

### 步骤
1. Colab新建笔记本
2. 装包+加载分子:
```python
!pip install -q rdkit scikit-learn
from rdkit import Chem
from rdkit.Chem import Descriptors
# 一个分子(咖啡因的SMILES)
mol = Chem.MolFromSmiles("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")
print("分子量:", Descriptors.MolWt(mol))
print("脂溶性:", Descriptors.MolLogP(mol))
```
3. 预测毒性/溶解度(用现成模型):
```python
# 下载一个分子毒性数据集(简化版),训练个简单模型预测毒性
# 这步可选,先感受"输入分子→输出性质"的闭环
```
4. **改一个分子结构,看预测性质怎么变——这就是"用AI预测化学性质"**

## 玩法3（进阶,若前两个让你兴奋）：材料发现 MatterGen

- 微软MatterGen: https://github.com/microsoft/mattergen (生成新材料)
- 环境: conda+pytorch,装2-3小时
- 跑通后:输入"我想要带隙>1.5eV的材料",生成候选材料结构
- **这个最贴你的物理本科门票,但门槛高,前两个喜欢再上**

## 玩完怎么判断

第27轮铁律(改写版):
- **ESMFold让你想换个蛋白再跑、想读原理、想看结构怎么变** → AI4Science对你有吸引力,值得深入
- **跑完觉得"酷但不是我的问题"/"就这"** → AI4Science不是你的菜,排除,别可惜物理本科门票(前33轮已说它直进企业研发岗难,需读硕)
- **完全不想碰代码** → 可能是burnout,该休息不是转岗

## 资源
- ESMFold官方: https://github.com/facebookresearch/esm
- AlphaFold colab: 直接搜"AlphaFold Colab"有官方版
- RDKit教程: https://www.rdkit.org/docs/Cookbook.html
- 深势科技(北京AI4Sci公司,可看招聘JD感受真实需求): https://www.dp.tech
- 晶泰科技: https://www.xtalpi.com

## 重要提醒
- 这是"玩",不是转岗作战。别想着"这能放简历吗"。放不放简历是后面的事。
- 跑不通就跳过(网络/环境问题正常),换下一个玩。
- 半小时不够就玩1小时,够了就停。别逼自己。
- 玩完只记一句:爽还是不爽,为什么。
