import os
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
                label="Question"
            ),
            gr.Dropdown(
                [question for question in questions.values()],
                label="Examples",
                info="Pick a question"
            )
        ],
        outputs=[
            gr.Textbox(label="Answer", lines=5),
            gr.Markdown(label="References")
        ],
        title="Feynbot: talking with INSPIRE",
        description=(
            'Developed by: <a href="https://sinai.ujaen.es/"><img src="https://sinai.ujaen.es/sites/default/files/SINAI%20-%20logo%20tx%20azul%20%5Baf%5D.png" alt="Feynbot" width="150"></a>'
            '<br>'
            '<p>Ask anything or pick an example question from the dropdown below.</p>'
        ),
        allow_flagging=config["gradio"]["allow_flagging"],
        flagging_dir=config["gradio"]["flagging_dir"]
    )

    demo.launch(
        server_name="0.0.0.0",
        share=config["gradio"]["share"],
        root_path="/feynbot",
        show_api=False,
        allowed_paths=["/"]
    )
