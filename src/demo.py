import json
import gradio as gr
from feynbot.app import get_response, load_config
from feynbot_ir.app import search

if __name__ == "__main__":
    config = load_config("config.yaml")
    with open(config["gradio"]["questions"], "r") as f:
        questions = json.load(f)

    FOOTER = ('Developed by: <img src="https://sinai.ujaen.es/sites/default/files/SINAI%20-%20logo%20tx%20azul%20%5Baf%5D.png" alt="Feynbot" width="150">'
              "Hosted at CERN by the SIS team")

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
        title="Feynbot",
        description="Ask anything or pick an example question from the dropdown below.",
        allow_flagging=config["gradio"]["allow_flagging"],
        flagging_dir=config["gradio"]["flagging_dir"],
        article=FOOTER,
    )

    with gr.Blocks() as feynbot_ir:
        gr.Markdown("<h1 style='text-align: center;'>Feynbot on INSPIRE HEP Search</h1>")
        gr.Markdown("""Specialized academic search tool that combines traditional 
                    database searching with AI-powered query expansion and result 
                    synthesis, focused on physics research papers.""")
        with gr.Row():
            with gr.Column():
                query = gr.Textbox(label="Search Query", placeholder="Ask Feynbot anything...", lines=3)
                examples = gr.Examples([["Which one is closest star?"], ["In which particles does the Higgs Boson decay to?"]], query)
                search_btn = gr.Button("Search")
                gr.HTML(FOOTER)
            with gr.Column():
                results = gr.Markdown("Answer will appear here...", label="Search Results", )
            search_btn.click(fn=search, inputs=query, outputs=results, api_name="search", show_progress=True)

    demo = gr.TabbedInterface(
        [feynbot, feynbot_ir], ["Feynbot", "Feynbot IR"], theme="citrus"
    )

    demo.launch(
        server_name="0.0.0.0",
        share=config["gradio"]["share"],
        root_path="/feynbot",
        show_api=False,
        debug=True,
    )
