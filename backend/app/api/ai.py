from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def run_agent(system_prompt: str, user_input: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"