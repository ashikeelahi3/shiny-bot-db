import os
import duckdb
import faicons as fa
from dotenv import load_dotenv
from pathlib import Path
from chatlas import ChatGoogle, ChatOpenAI
from shiny import App, ui, render, reactive

import query
from shared import tips

here = Path(__file__).parent
icon_ellipsis = fa.icon_svg("ellipsis")
icon_explain = ui.img(src="stars.svg")

greetings = """
You can use this sidebar to filter and sort the data based on the columns available in the `tips` table. Here are some examples of the kinds of questions you can ask me:

1. Filtering: <span class="suggestion">Show only Male smokers who had Dinner on Saturday.</span>
2. Sorting: <span class="suggestion">Show all data sorted by total_bill in descending order.</span>
3. Answer questions about the data: <span class="suggestion">How do tip sizes compare between lunch and dinner?</span>

You can also say <span class="suggestion">Reset</span> to clear the current filter/sort, or <span class="suggestion">Help</span> for more usage tips.
"""

# app_ui = ui.page_sidebar( 
#     ui.sidebar(
#         ui.chat_ui(id="chat", messages=[ greetings ], height="100%"),
#         ui.input_radio_buttons(
#             "model",  
#             "Choose Model",  
#             {"gemini-2.0-flash": "Gemini 2.0 Flash", "gpt-4o-mini": "GPT-4o Mini"},
#             inline=True
#         ),
#         width=450, style="height:100%" #, title="Chatbot"
#     ),
#     ui.page_fluid(
#         ui.div(id="dynamic_ui_container")
#     )
# )


app_ui = ui.page_fluid(
    ui.navset_tab(  
      ui.nav_panel("ChatBot",
        ui.page_sidebar(
          ui.sidebar(
            ui.chat_ui(id="chat", messages=[ greetings ], height="100%"),
            ui.input_radio_buttons(
                          "model",  
                          "Choose Model",  
                          {"gemini-2.0-flash": "Gemini 2.0 Flash", "gpt-4o-mini": "GPT-4o Mini"},
                          inline=True
                      ),
                      width=450, style="height:100%" #, title="Chatbot"
                  ),
                  ui.page_fluid(
                      # ui.div(id="dynamic_ui_container")
											#
											# 🏷️ Header
											#
											ui.output_text("show_title", container=ui.h3),
											ui.output_code("show_query", placeholder=False).add_style(
													"max-height: 100px; overflow: auto;"
											),
											#
											# 🎯 Value boxes
											#
											ui.layout_columns(
													ui.value_box(
															"Total tippers",
															ui.output_text("total_tippers"),
															showcase=fa.icon_svg("user", "regular"),
													),
													ui.value_box(
															"Average tip", ui.output_text("average_tip"), showcase=fa.icon_svg("wallet")
													),
													ui.value_box(
															"Average bill",
															ui.output_text("average_bill"),
															showcase=fa.icon_svg("dollar-sign"),
													),
													fill=False,
											),
                  )
              ),
              
            ),
        ui.nav_panel("Data Visualization",
          
					# 🔍 Data table
					ui.card(
							ui.card_header("Tips data"),
							ui.output_data_frame("table"),
							full_screen=False,
					), 
					            
				),
        id="tab",  
    ), height="100%"
      
)

def server(input, output, session):
	load_dotenv()

	current_query = reactive.Value("")
	current_title = reactive.Value("")
	
	# Store conversation history as a list of message dictionaries
	conversation_history = reactive.value([])
	
	def create_chat_client(model_name):
		"""Create a fresh chat client for the specified model"""
		if model_name == "gemini-2.0-flash":
			client = ChatGoogle(
				api_key=os.environ.get("GOOGLE_API_KEY"),
				system_prompt="""
				You are a helpful chatbot that can analyze data and answer questions.
				Previous conversation context will be provided to maintain continuity.
				""",
				model="gemini-2.0-flash-exp",
			)
		else:  # gpt-4o-mini
			client = ChatOpenAI(
				api_key=os.environ.get("OPENAI_API_KEY"),
				system_prompt="""
				You are a helpful chatbot that can analyze data and answer questions.
				Previous conversation context will be provided to maintain continuity.
				""",
				model="gpt-4o-mini",
			)
		client.register_tool(update_dashboard)
		client.register_tool(query_db)
		return client	

	def get_chat_client_with_history(model_name):
		"""Get chat client and provide conversation history as context"""
		# Build context from conversation history
		history = conversation_history.get()
		context_messages = []
		
		if history:
			# Convert history to context string
			context_parts = []
			for msg in history:
				if msg["role"] == "user":
					context_parts.append(f"User: {msg['content']}")
				else:  # assistant
					model_used = msg.get("model", "Assistant")
					context_parts.append(f"{model_used}: {msg['content']}")
			
			conversation_context = "\n\n".join(context_parts)
		else:
				conversation_context = ""
		

		

		# Create chat client with enhanced system prompt including context
		system_prompt = query.system_prompt(tips, "tips")
		
		if conversation_context:
			system_prompt += f"""
		Here is the previous conversation context to maintain continuity:
		
		{conversation_context}
		"""
		
		if model_name == "gemini-2.0-flash":
			client = ChatGoogle(
				api_key=os.environ.get("GOOGLE_API_KEY"),
				system_prompt=system_prompt,
				model="gemini-2.0-flash-exp",
			)
		else:  # gpt-4o-mini
			client = ChatOpenAI(
				api_key=os.environ.get("OPENAI_API_KEY"),
				system_prompt=system_prompt,
				model="gpt-4o-mini",
			)
		client.register_tool(update_dashboard)
		client.register_tool(query_db)
		return client	
	
	chat = ui.Chat(id="chat")


		
	@reactive.calc
	def tips_data():
		if current_query() == "":
			return tips
		return duckdb.query(current_query()).df()
	
	@render.text
	def show_title():
		return current_title()
	
	@render.text
	def show_query():
		return current_query()
	
	# 🎯 Value box outputs -----------------------------------------------------
	@render.text
	def total_tippers():
		return str(tips_data().shape[0])
	
	@render.text
	def average_tip():
		d = tips_data()
		if d.shape[0] > 0:
			perc = d.tip / d.total_bill
			return f"{perc.mean():.1%}"

	@render.text
	def average_bill():
		d = tips_data()
		if d.shape[0] > 0:
			return f"${d.total_bill.mean():.2f}"
		

	# 🔍 Data table ------------------------------------------------------------
	@render.data_frame
	def table():
		return render.DataGrid(tips_data())

	@chat.on_user_submit
	async def handle_user_input(user_input: str):
		try:
			current_model = input.model()
			
			# Add user message to conversation history
			history = conversation_history.get().copy()
			history.append({"role": "user", "content": user_input})
			conversation_history.set(history)
			
			# Get chat client with full conversation history
			chat_client = get_chat_client_with_history(current_model)

			
			
			# Get response from the model (it now has full context)
			response_stream = await chat_client.stream_async(user_input)
			full_response = ""
			
			# Collect the full response
			async for chunk in response_stream:
					full_response += chunk
			
			# Add assistant response to conversation history
			history = conversation_history.get().copy()
			history.append({"role": "assistant", "content": full_response, "model": current_model})
			conversation_history.set(history)
			
			# Display response in chat UI
			await chat.append_message(full_response)
				
		except Exception as e:
			error_msg = f"Error with {input.model()}: {str(e)}"
			print(error_msg)
			await chat.append_message(f"**Error:** Failed to get response from {input.model()}. Please check your API keys and try again.")
    
	async def update_filter(query, title):
		# Need this reactive lock/flush because we're going to call this from a
		# background asyncio task
		async with reactive.lock():
			current_query.set(query)
			current_title.set(title)
			await reactive.flush()	

	async def update_dashboard(
		query: str,
		title: str,
  ):
		"""Modifies the data presented in the data dashboard, based on the given SQL query, and also updates the title.

			Args:
				query: A DuckDB SQL query; must be a SELECT statement, or an empty string to reset the dashboard.
				title: A title to display at the top of the data dashboard, summarizing the intent of the SQL query.
  	""" 			 
		# Verify that the query is OK; throws if not
		if query != "":
			await query_db(query)
			await update_filter(query, title)

	async def query_db(query: str):
		"""Perform a SQL query on the data, and return the results as JSON.

		Args:
			query: A DuckDB SQL query; must be a SELECT statement.
		"""
		return duckdb.query(query).to_df().to_json(orient="records")

	


    # # Optional: Add a button to clear conversation history
    # @render.ui
    # def clear_history_button():
    #     return ui.div(
    #         ui.input_action_button("clear_history", "Clear History", class_="btn-warning btn-sm"),
    #         style="margin-top: 10px;"
    #     )
    
    # @reactive.effect
    # @reactive.event(input.clear_history)
    # def clear_conversation():
    #     conversation_history.set([])
    #     print("Conversation history cleared")
    
	

app = App(app_ui, server)