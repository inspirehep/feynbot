import json
from os import getenv

import gradio as gr
from dotenv import load_dotenv
from feynbot_ir.app import search as ir_search
from feynbot_ir.app_fulltext import search as ir_ft_search

from feynbot.app import get_response, load_config

load_dotenv()

if __name__ == "__main__":
    config = load_config("config.yaml")
    with open(config["gradio"]["questions"], "r") as f:
        questions = json.load(f)

    FOOTER = (
        'Developed by: <img src="https://sinai.ujaen.es/sites/default/files/SINAI%20-%20logo%20tx%20azul%20%5Baf%5D.png" alt="Feynbot" width="150">'
        "Hosted at CERN by the SIS team"
    )

    feynbot = gr.Interface(
        fn=get_response,
        inputs=[
            gr.Textbox(
                value="",
                lines=3,
                placeholder="Ask Feynbot anything...",
                label="Question",
            ),
            gr.Dropdown(
                [question for question in questions.values()],
                label="Examples",
                info="Pick a question",
            ),
        ],
        outputs=[gr.Textbox(label="Answer", lines=5), gr.Markdown(label="References")],
        title="Feynbot Base",
        description="Ask anything or pick an example question from the dropdown below.",
        allow_flagging=config["gradio"]["allow_flagging"],
        flagging_dir=config["gradio"]["flagging_dir"],
        article=FOOTER,
    )

    with gr.Blocks() as feynbot_ir:
        gr.Markdown(
            "<h1 style='text-align: center;'>Feynbot IR on INSPIRE HEP Search</h1>"
        )
        gr.Markdown("""Specialized academic search tool that combines traditional 
                    database searching with AI-powered query expansion and result 
                    synthesis (from retrieved abstracts), focused on High Energy 
                    Physics research papers.""")
        with gr.Row():
            with gr.Column():
                query = gr.Textbox(
                    label="Search Query", placeholder="Ask Feynbot anything...", lines=3
                )
                model = gr.Dropdown(
                    choices=getenv("VALID_MODELS").split(","),
                    value=getenv("DEFAULT_MODEL"),
                    label="Model (select or free-text)",
                    allow_custom_value=True,
                )
                examples = gr.Examples(
                    [
                        ["Which is the closest star?"],
                        ["Which particles does the Higgs Boson decay into?"],
                    ],
                    query,
                )
                search_btn = gr.Button("Search")
                gr.HTML(FOOTER)
            with gr.Column():
                results = gr.Markdown(
                    "Answer will appear here...",
                    label="Search Results",
                )
            search_btn.click(
                fn=ir_search,
                inputs=[query, model],
                outputs=results,
                api_name="search",
                show_progress=True,
            )

    with gr.Blocks() as feynbot_fulltext:
        gr.Markdown("<h1 style='text-align: center;'>Feynbot Fulltext Search</h1>")
        gr.Markdown("""Search through the full text content of physics research papers 
                    in the INSPIRE HEP database using AI-powered query expansion and 
                    result synthesis.""")
        with gr.Row():
            with gr.Column():
                query = gr.Textbox(
                    label="Search Query",
                    placeholder="Search through paper content...",
                    lines=3,
                )
                model = gr.Dropdown(
                    choices=getenv("VALID_MODELS").split(","),
                    value=getenv("DEFAULT_MODEL"),
                    label="Model (select or free-text)",
                    allow_custom_value=True,
                )
                examples = gr.Examples(
                    [
                        ["What are the experimental signatures of dark matter?"],
                        ["How is supersymmetry broken?"],
                    ],
                    query,
                )
                search_btn = gr.Button("Search")
                gr.HTML(FOOTER)
            with gr.Column():
                results = gr.Markdown(
                    "Results will appear here...",
                    label="Search Results",
                )
            search_btn.click(
                fn=ir_ft_search,
                inputs=[query, model],
                outputs=results,
                api_name="fulltext_search",
                show_progress=True,
            )

    demo = gr.TabbedInterface(
        [feynbot_ir, feynbot_fulltext, feynbot],
        ["Feynbot IR", "Feynbot IR Fulltext", "Feynbot Base"],
        theme="citrus",
    )

    demo.launch(
        server_name="0.0.0.0",
        share=config["gradio"]["share"],
        root_path="/feynbot",
        show_api=False,
        debug=True,
    )
