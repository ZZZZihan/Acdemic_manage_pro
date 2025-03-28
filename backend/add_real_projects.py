from app import create_app
from app.models import db
from app.models.achievement import Achievement
from app.models.user import User
from datetime import datetime
import os

app = create_app(os.getenv('FLASK_CONFIG') or 'default')

with app.app_context():
    # 获取管理员用户
    admin = User.query.filter_by(email='admin@example.com').first()
    
    if not admin:
        print('未找到默认管理员账户，无法添加成果记录。')
        exit(1)
    
    # 准备真实项目数据
    real_projects = [
        {
            'title': 'TensorFlow - 开源机器学习框架',
            'description': 'TensorFlow是Google开发的开源机器学习框架，用于构建和训练深度学习模型。它提供了灵活的架构，支持多种平台部署，包括服务器、云、移动设备和边缘设备。该项目在计算机视觉、自然语言处理、语音识别等领域被广泛应用。',
            'achievement_type': '项目',
            'authors': 'Google AI Research Team',
            'publish_date': datetime.now(),
            'url': 'https://www.tensorflow.org/',
            'file_path': 'uploads/projects/medical_imaging.jpg',
            'original_file_name': 'tensorflow.jpg',
            'user_id': admin.id
        },
        {
            'title': 'PyTorch - 灵活的深度学习研究平台',
            'description': 'PyTorch是由Facebook的AI研究实验室开发的开源深度学习框架，特点是动态计算图和直观的Python接口。它在研究社区特别受欢迎，因为其设计理念非常灵活，易于调试和实验。项目支持GPU加速计算，提供丰富的工具和库生态系统。',
            'achievement_type': '项目',
            'authors': 'Facebook AI Research',
            'publish_date': datetime.now(),
            'url': 'https://pytorch.org/',
            'file_path': 'uploads/projects/environment.png',
            'original_file_name': 'pytorch.jpg',
            'user_id': admin.id
        },
        {
            'title': 'BERT - 双向Transformer预训练语言模型',
            'description': 'BERT (Bidirectional Encoder Representations from Transformers) 是Google AI Language团队开发的预训练语言表示模型，通过双向训练Transformer模型来理解词语在上下文中的含义。BERT在多个自然语言处理任务中创造了新的SOTA结果，包括问答、情感分析和语言推理等。',
            'achievement_type': '项目',
            'authors': 'Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova',
            'publish_date': datetime.now(),
            'url': 'https://github.com/google-research/bert',
            'file_path': 'uploads/projects/education.jpg',
            'original_file_name': 'bert.jpg',
            'user_id': admin.id
        },
        {
            'title': 'DALL-E - 从文本生成图像的AI系统',
            'description': 'DALL-E是OpenAI开发的AI系统，能够从文本描述生成详细的图像。它使用GPT-3的变体训练，能够创建逼真的图像和艺术作品，仅基于文字描述。DALL-E展示了大型模型在跨模态学习方面的令人印象深刻的能力，为创意内容生成开辟了新的可能性。',
            'achievement_type': '项目',
            'authors': 'OpenAI Research Team',
            'publish_date': datetime.now(),
            'url': 'https://openai.com/dall-e/',
            'file_path': 'uploads/projects/smart_campus.png',
            'original_file_name': 'dalle.jpg',
            'user_id': admin.id
        },
        {
            'title': 'AlphaFold - 革命性蛋白质结构预测AI',
            'description': 'AlphaFold是DeepMind开发的人工智能系统，用于预测蛋白质的3D结构。该系统在CASP14竞赛中取得了突破性成果，预测精度达到原子级别。AlphaFold解决了困扰生物学界50多年的蛋白质折叠问题，为药物发现、疾病理解和生物技术领域带来巨大影响。',
            'achievement_type': '项目',
            'authors': 'DeepMind Research Team',
            'publish_date': datetime.now(),
            'url': 'https://deepmind.com/research/case-studies/alphafold',
            'file_path': 'uploads/projects/blockchain.png',
            'original_file_name': 'alphafold.jpg',
            'user_id': admin.id
        },
        {
            'title': 'Linux内核 - 开源操作系统核心',
            'description': 'Linux内核是世界上最广泛使用的开源操作系统内核，由Linus Torvalds创建并由全球开发者社区维护。它为各种计算设备提供基础，从超级计算机到嵌入式系统和手机。Linux内核的成功展示了开源协作模式的有效性，为整个软件产业提供了重要的基础设施。',
            'achievement_type': '项目',
            'authors': 'Linus Torvalds与全球开源社区',
            'publish_date': datetime.now(),
            'url': 'https://www.kernel.org/',
            'file_path': 'uploads/projects/maintenance.png',
            'original_file_name': 'linux.jpg',
            'user_id': admin.id
        },
        {
            'title': 'Kubernetes - 容器编排平台',
            'description': 'Kubernetes是Google开源的容器编排平台，用于自动化部署、扩展和管理容器化应用程序。它已成为云原生基础设施的核心，能有效管理微服务架构和分布式系统。Kubernetes支持多云和混合云环境，提供强大的自愈、负载均衡和服务发现功能。',
            'achievement_type': '项目',
            'authors': 'Google与Cloud Native Computing Foundation社区',
            'publish_date': datetime.now(),
            'url': 'https://kubernetes.io/',
            'file_path': 'uploads/projects/traffic.jpg',
            'original_file_name': 'kubernetes.jpg',
            'user_id': admin.id
        },
        {
            'title': 'React - 用户界面构建库',
            'description': 'React是Facebook开发的JavaScript库，用于构建用户界面，特别是单页应用程序。其核心是组件化设计理念和虚拟DOM，使开发者能够创建高效、可重用的UI组件。React已成为前端开发的主流框架之一，拥有庞大的生态系统和活跃的开发者社区。',
            'achievement_type': '项目',
            'authors': 'Facebook与开源社区',
            'publish_date': datetime.now(),
            'url': 'https://reactjs.org/',
            'file_path': 'uploads/projects/chatbot.jpg',
            'original_file_name': 'react.jpg',
            'user_id': admin.id
        },
        {
            'title': 'Stable Diffusion - 开源文本到图像生成模型',
            'description': 'Stable Diffusion是一种开源的文本到图像生成模型，由Stability AI与研究机构合作开发。该模型基于潜在扩散模型，能够从文本描述生成精美的图像，在艺术创作、设计和内容创建领域产生广泛影响。模型开源使AI图像生成变得更加普及和民主化。',
            'achievement_type': '项目',
            'authors': 'Stability AI, CompVis, LAION',
            'publish_date': datetime.now(),
            'url': 'https://stability.ai/stable-diffusion',
            'file_path': 'uploads/projects/agriculture.jpg',
            'original_file_name': 'stable_diffusion.jpg',
            'user_id': admin.id
        },
        {
            'title': 'GPT-4 - 先进的大型语言模型',
            'description': 'GPT-4是OpenAI开发的大型语言模型，代表了NLP领域的重大突破。相比前代模型，它具有更强的推理能力、更广的知识面和更好的指令遵循能力。GPT-4能够理解和生成自然语言和代码，展示了类似人类的理解和推理能力，在多个行业中有广泛的应用潜力。',
            'achievement_type': '项目',
            'authors': 'OpenAI Research Team',
            'publish_date': datetime.now(),
            'url': 'https://openai.com/gpt-4',
            'file_path': 'uploads/projects/telemedicine.png',
            'original_file_name': 'gpt4.jpg',
            'user_id': admin.id
        }
    ]
    
    # 检查数据库中是否已存在这些项目
    existing_titles = [a.title for a in Achievement.query.all()]
    new_projects = []
    
    for project in real_projects:
        if project['title'] not in existing_titles:
            new_projects.append(project)
    
    # 添加新项目到数据库
    if new_projects:
        for project_data in new_projects:
            project = Achievement(**project_data)
            db.session.add(project)
        
        db.session.commit()
        print(f'成功添加 {len(new_projects)} 个真实项目成果记录到数据库')
    else:
        print('所有项目已存在于数据库中，未添加新记录')
    
    # 显示当前所有成果记录
    all_achievements = Achievement.query.all()
    print(f'数据库中现有 {len(all_achievements)} 个成果记录：')
    for i, achievement in enumerate(all_achievements):
        print(f'{i+1}. {achievement.title} - {achievement.achievement_type} - {achievement.authors}') 