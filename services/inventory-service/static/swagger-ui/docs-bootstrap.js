window.addEventListener("load", () => {
  const root = document.getElementById("swagger-ui");
  if (!root || !window.SwaggerUIBundle) {
    return;
  }

  const ui = window.SwaggerUIBundle({
    url: root.dataset.openapiUrl,
    dom_id: "#swagger-ui",
    layout: "BaseLayout",
    deepLinking: true,
    showExtensions: true,
    showCommonExtensions: true,
    persistAuthorization: true,
    displayRequestDuration: true,
    tryItOutEnabled: true,
    defaultModelsExpandDepth: 1,
    docExpansion: "list",
    oauth2RedirectUrl: root.dataset.oauth2RedirectUrl,
    presets: [window.SwaggerUIBundle.presets.apis],
  });

  if (root.dataset.defaultApiKey) {
    ui.preauthorizeApiKey("APIKeyHeader", root.dataset.defaultApiKey);
  }
});
