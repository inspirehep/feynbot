import gradio as gr
from openai_starter import get_response

def greet(name, intensity):
    return "Hello, " + name + "!" * int(intensity)

demo = gr.Interface(
    fn=get_response,
    inputs=["text"],
    outputs=["text"],
    flagging_dir="../flagged"
)

demo.launch(share=True)