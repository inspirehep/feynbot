import json
import gradio as gr
from utils import get_response, load_config

if __name__ == "__main__":
    config = load_config("config.yaml")
    with open(config["gradio"]["questions"], "r") as f:
        questions = json.load(f)

    demo = gr.Interface(
        fn=get_response,
        inputs=[
            gr.Textbox(
                value="",
                lines=3,
                placeholder="Ask Feynbot anything...",
                label="Query"
            ),
            gr.Dropdown(
                [question for question in questions.values()],
                label="Example queries",
                info="Pick a question"
            )
        ],
        outputs=[
            gr.Textbox(label="Output", lines=3),
            gr.Textbox(label="References", lines=3)
        ],
        title="Feynbot: talking with INSPIRE",
        allow_flagging=config["gradio"]["allow_flagging"],
        flagging_dir=config["gradio"]["flagging_dir"]
    )

    demo.launch(
        server_name="0.0.0.0",
        share=config["gradio"]["share"],
        root_path="/feynbot",
        show_api=False
    )
