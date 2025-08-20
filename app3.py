from shiny import App, ui

app_ui = ui.page_fluid(
    ui.navset_tab(  
      ui.nav_panel("ChatBot",
        ui.page_sidebar(
          ui.sidebar(
            ui.chat_ui(id="chat", messages=[ "hi" ], height="100%"),
            ui.input_radio_buttons(
                          "model",  
                          "Choose Model",  
                          {"gemini-2.0-flash": "Gemini 2.0 Flash", "gpt-4o-mini": "GPT-4o Mini"},
                          inline=True
                      ),
                      width=450, style="height:100%" #, title="Chatbot"
                  ),
                  ui.page_fluid(
                      ui.div(id="dynamic_ui_container")
                  )
              )
            ),
        ui.nav_panel("B", "Panel B content"),
        ui.nav_panel("C", "Panel C content"),
        id="tab",  
    )  
)


def server(input, output, session):
    pass


app = App(app_ui, server)