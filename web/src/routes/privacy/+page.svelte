<script lang="ts">
	import Notice from '$lib/components/Notice.svelte';
	import PlateBand from '$lib/components/PlateBand.svelte';
	import { pageTitle, SITE_NAME, DOMAIN_NAME } from '$lib/site';
	import { CONTACT_EMAIL } from '$lib/owner';
	import { ADS_ENABLED } from '$lib/ads';
</script>

<svelte:head>
	<title>{pageTitle('Privacy')}</title>
	<meta name="description" content="What this site collects and what it sets on your device." />
</svelte:head>

<PlateBand title="Privacy" />

<main class="page privacy">
	{#if ADS_ENABLED}
		<article class="privacy-copy">
			<p id="privacy-updated" class="updated">Last updated: August 21, 2026</p>

			<section>
				<p>
					{SITE_NAME} ("we," "us," or "our") provides machine learning-based predictions for
					upcoming NBA games at {DOMAIN_NAME} (the "Site"). This Privacy Policy explains
					what information we collect, how we use it, and the choices you have. We do not
					require account creation to use the Site, and we do not sell your personal information.
				</p>
				<p>By using the Site, you agree to the practices described in this policy.</p>
			</section>

			<section>
				<h2>1. Information We Collect</h2>
				<h3>Information You Provide Directly</h3>
				<p>
					The Site does not require registration or an account. The only time we receive information
					directly from you is if you choose to email us — for example, using the contact address
					below. In that case, we receive your email address and whatever you include in your message.
				</p>
				<h3>Information Collected Automatically</h3>
				<p>When you visit the Site, certain information is collected automatically, including:</p>
				<ul>
					<li>IP address (used to derive general/approximate location, e.g., city or region)</li>
					<li>Browser type and version</li>
					<li>Device and operating system information</li>
					<li>Pages viewed, time spent on pages, and referring/exit URLs</li>
					<li>Date and time of visits</li>
				</ul>
				<p>
					This information is collected through standard server logs, cookies, and the third-party
					tools described below (Google AdSense and Google Analytics). We use it in aggregate to
					understand traffic and usage patterns — we do not use it to identify you personally.
				</p>
				<h3>Cookies and Similar Technologies</h3>
				<p>Cookies are small text files stored on your device. The Site uses cookies for two purposes:</p>
				<ul>
					<li>Advertising — served through Google AdSense</li>
					<li>Analytics — served through Google Analytics</li>
				</ul>
				<p>
					You can control or disable cookies through your browser settings. Disabling cookies may affect
					how ads are displayed but will not prevent you from viewing predictions on the Site.
				</p>
			</section>

			<section>
				<h2>2. Advertising (Google AdSense)</h2>
				<p>
					The Site displays ads through Google AdSense. Google and its partners may use cookies
					(including the DoubleClick cookie) to serve ads based on your prior visits to this and other
					websites, and to measure ad performance.
				</p>
				<p>Google's use of advertising cookies enables it and its partners to serve ads based on your visits to this and other sites.</p>
				<p>You can opt out of personalized advertising by visiting Google Ads Settings or, for a broader industry opt-out, www.aboutads.info/choices.</p>
				<p>More detail on how Google handles data for advertising is available at Google's Privacy &amp; Terms site.</p>
				<p>We do not control the specific ads shown to you, and we do not have access to the personal data Google collects for ad targeting.</p>
			</section>

			<section>
				<h2>3. Analytics (Google Analytics)</h2>
				<p>
					We use Google Analytics to understand how visitors use the Site — for example, which pages
					are popular and how people navigate the Site. Google Analytics collects information such as
					pages visited, session duration, approximate location (derived from IP address), and
					device/browser type.
				</p>
				<p>This data is used in aggregate and is not used by us to identify individual visitors.</p>
				<p>You can prevent Google Analytics from tracking your visit by installing the Google Analytics Opt-out Browser Add-on.</p>
				<p>Learn more about how Google handles data in this context at Google's Privacy Policy.</p>
			</section>

			<section>
				<h2>4. How We Use Information</h2>
				<p>We use the information described above to:</p>
				<ul>
					<li>Operate and maintain the Site</li>
					<li>Understand and improve Site traffic, performance, and usage patterns</li>
					<li>Display and measure the performance of ads</li>
					<li>Respond to emails or inquiries you send us</li>
				</ul>
				<p>We do not use any collected information to make decisions about individual users, and we do not sell personal information to third parties.</p>
			</section>

			<section>
				<h2>5. Third-Party Service Providers</h2>
				<p>We share limited data (primarily automatically-collected data described in Section 1) with the following third-party service providers, each of which has its own privacy policy governing its use of that data:</p>
				<ul>
					<li>Google AdSense — advertising</li>
					<li>Google Analytics — site analytics</li>
				</ul>
				<p>We do not share data with any other third parties for marketing or advertising purposes.</p>
			</section>

			<section>
				<h2>6. Do Not Track</h2>
				<p>Some browsers offer a "Do Not Track" (DNT) signal. There is currently no industry-standard way to respond to DNT signals, so the Site does not currently alter its data collection in response to them.</p>
			</section>

			<section>
				<h2>7. Children's Privacy</h2>
				<p>The Site is not directed at children under the age of 13, and we do not knowingly collect personal information from children under 13. If you believe a child has provided us with personal information (for example, by email), please contact us so we can delete it.</p>
			</section>

			<section>
				<h2>8. Your Choices</h2>
				<p>Because the Site doesn't have accounts, there's very little personal data tied to you individually. Your main choices are:</p>
				<ul>
					<li>Cookies: Adjust or block cookies through your browser settings.</li>
					<li>Personalized ads: Opt out via Google Ads Settings or aboutads.info.</li>
					<li>Analytics: Opt out via the Google Analytics Opt-out Add-on.</li>
					<li>Email data: If you've emailed us, you can request that we delete that correspondence by contacting us at the address below.</li>
				</ul>
				<p>Depending on your state of residence, you may have additional rights under applicable state privacy laws regarding access to or deletion of information we hold about you. Since we collect minimal personal data and don't maintain user profiles, most such requests can be handled simply by contacting us directly.</p>
			</section>

			<section>
				<h2>9. Data Security</h2>
				<p>We take reasonable measures to protect the limited information we handle, but no method of transmission or storage over the internet is completely secure. We cannot guarantee absolute security.</p>
			</section>

			<section>
				<h2>10. Third-Party Links</h2>
				<p>The Site may link to third-party websites (for example, NBA stats or news sources). We are not responsible for the privacy practices or content of those sites. We encourage you to review the privacy policy of any site you visit.</p>
			</section>

			<section>
				<h2>11. Changes to This Privacy Policy</h2>
				<p>We may update this Privacy Policy from time to time. Changes will be posted on this page with a revised "Effective Date." Your continued use of the Site after changes are posted constitutes acceptance of the updated policy.</p>
			</section>

			<section>
				<h2>12. Contact Us</h2>
				<p>If you have questions about this Privacy Policy or how your information is handled, contact us at:</p>
				<p>{CONTACT_EMAIL}</p>
			</section>
		</article>
	{:else}
		<Notice tone="warning">
			This page is not written. No ads and no analytics currently run on this site.
		</Notice>
	{/if}
</main>

<style>
	.page {
		padding-block: var(--space-7) var(--space-8);
	}

	.privacy-copy {
		font-family: var(--font-ui);
		font-size: clamp(1.0625rem, 1vw + 0.8rem, 1.1875rem);
		line-height: 1.65;
	}

	.updated {
		padding-block-end: var(--space-5);
		border-bottom: var(--rule-panel);
		font-family: var(--font-ui);
		font-size: var(--type-small);
		font-weight: 600;
		letter-spacing: 0.01em;
	}

	section {
		display: grid;
		gap: var(--space-4);
		padding-block-start: var(--space-6);
	}

	section + section {
		margin-block-start: var(--space-5);
		border-top: var(--rule-panel);
	}

	h2,
	h3 {
		font-family: var(--font-ui);
		font-weight: 700;
		letter-spacing: 0.01em;
	}

	h2 {
		font-size: var(--type-h3);
		line-height: 1.35;
	}

	h3 {
		font-size: var(--type-note);
		line-height: 1.35;
	}

	ul {
		display: grid;
		gap: var(--space-3);
		padding-inline-start: 1.25em;
	}

	li::marker {
		color: var(--plane-accent);
	}

	@media (width < 40rem) {
		.page {
			padding-block: var(--space-6) var(--space-7);
		}

		section {
			padding-block-start: var(--space-5);
		}

		section + section {
			margin-block-start: var(--space-4);
		}
	}
</style>
