import os
from dotenv import load_dotenv
from chatlas import ChatGoogle, ChatOpenAI
from shiny import App, ui, render, reactive


app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.chat_ui(id="chat", messages=[
            """Welcome to the Shiny App! I can help you analyze the tippers dataset. What would you like to see? 
            """
        ], height="100%"),
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

def server(input, output, session):
    load_dotenv()
    
    # Store conversation history as a list of message dictionaries
    conversation_history = reactive.value([])
    
    def create_chat_client(model_name):
        """Create a fresh chat client for the specified model"""
        if model_name == "gemini-2.0-flash":
            return ChatGoogle(
                api_key=os.environ.get("GOOGLE_API_KEY"),
                system_prompt="""
                You are a helpful chatbot that can analyze data and answer questions.
                Previous conversation context will be provided to maintain continuity.
                """,
                model="gemini-2.0-flash-exp",
            )
        else:  # gpt-4o-mini
            return ChatOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                system_prompt="""
                You are a helpful chatbot that can analyze data and answer questions.
                Previous conversation context will be provided to maintain continuity.
                """,
                model="gpt-4o-mini",
            )
    
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
        system_prompt = """
        You are a helpful chatbot that can analyze data and answer questions.
        
        """
        
        if conversation_context:
            system_prompt += f"""
        Here is the previous conversation context to maintain continuity:
        
        {conversation_context}
        
        Continue the conversation naturally, acknowledging the previous context.
        """
        
        if model_name == "gemini-2.0-flash":
            return ChatGoogle(
                api_key=os.environ.get("GOOGLE_API_KEY"),
                system_prompt=system_prompt,
                model="gemini-2.0-flash-exp",
            )
        else:  # gpt-4o-mini
            return ChatOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                system_prompt=system_prompt,
                model="gpt-4o-mini",
            )
    
    chat = ui.Chat(id="chat")
    
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