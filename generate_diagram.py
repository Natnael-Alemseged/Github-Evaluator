import os
from src.graph import app

def main():
    try:
        png_data = app.get_graph().draw_mermaid_png()
        with open("architecture.png", "wb") as f:
            f.write(png_data)
        print("Generated architecture.png successfully!")
    except Exception as e:
        print(f"Failed to generate diagram: {e}")

if __name__ == "__main__":
    main()
