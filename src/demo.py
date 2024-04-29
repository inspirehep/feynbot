import os
import gradio as gr

from utils import get_response, load_config

if __name__ == "__main__":
    config = load_config("config.yaml")

    demo = gr.Interface(
        fn=get_response,
        inputs=[
            gr.Textbox(
                value=(
                    "How does the 1-loop Rényi entropy in LCFT compare to "
                    "that in ordinary CFT, particularly regarding the "
                    "introduction of a new primary operator and the "
                    "contributions of quasiprimary operators?"
                ),
                label="Input",
                lines=3
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

    demo.launch(share=config["gradio"]["share"], allowed_paths=["./"])
