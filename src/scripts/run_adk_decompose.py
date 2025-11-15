import asyncio
from agents.coordinator import CoordinatorAgent

async def main():
    agent = CoordinatorAgent()
    tasks = await agent.run_adk_decomposition("Analyze GNN for molecular property prediction")
    print("Decomposed tasks:", tasks)

if __name__ == '__main__':
    asyncio.run(main())
