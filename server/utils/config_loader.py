import yaml

from dotenv import load_dotenv

def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == "__main__":
    load_dotenv()
    config_path = r"E:\Workplace\Learning\Langchain\01_codeRAG\config.yaml"
    config = load_config(config_path)
    print("Configuration:")
    print(yaml.dump(config))