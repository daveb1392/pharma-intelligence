"""Main entry point for Apify Actor - runs selected pharmacy scrapers."""

import asyncio
import os
from apify import Actor
from scrapers import farma_oliva, punto_farma, farmacia_center, farmacia_catedral


async def main():
    """Main Actor entry point."""
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        pharmacy = actor_input.get('pharmacy', 'all')
        punto_farma_phase = actor_input.get('punto_farma_phase', 'phase1')
        farma_center_phase = actor_input.get('farma_center_phase', 'phase1')
        farma_catedral_phase = actor_input.get('farma_catedral_phase', 'phase1')

        Actor.log.info(f"Starting scraper for: {pharmacy}")
        if pharmacy == 'punto_farma':
            Actor.log.info(f"Punto Farma phase: {punto_farma_phase}")
        elif pharmacy == 'farmacia_center':
            Actor.log.info(f"Farmacia Center phase: {farma_center_phase}")
        elif pharmacy == 'farmacia_catedral':
            Actor.log.info(f"Farmacia Catedral phase: {farma_catedral_phase}")

        # Run selected scraper(s)
        if pharmacy == 'all':
            Actor.log.info("Running all pharmacy scrapers sequentially...")
            await farma_oliva.main()
            await punto_farma.main(phase=punto_farma_phase)
            await farmacia_center.main(phase=farma_center_phase)
            await farmacia_catedral.main(phase=farma_catedral_phase)

        elif pharmacy == 'farma_oliva':
            await farma_oliva.main()

        elif pharmacy == 'punto_farma':
            await punto_farma.main(phase=punto_farma_phase)

        elif pharmacy == 'farmacia_center':
            await farmacia_center.main(phase=farma_center_phase)

        elif pharmacy == 'farmacia_catedral':
            await farmacia_catedral.main(phase=farma_catedral_phase)

        else:
            Actor.log.error(f"Unknown pharmacy: {pharmacy}")

        Actor.log.info("✓ Scraping completed successfully!")


if __name__ == '__main__':
    asyncio.run(main())
