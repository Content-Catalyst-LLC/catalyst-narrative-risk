(function(){
  "use strict";
  function text(value){return String(value||"").trim();}
  function lines(value){return text(value).split(/\r?\n/).map(function(x){return x.trim();}).filter(Boolean);}
  function escapeHtml(value){return String(value).replace(/[&<>"']/g,function(ch){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[ch];});}
  function slugify(value){return text(value).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"narrative-risk-brief";}
  function payload(form){
    var data=new FormData(form);
    return {
      contract_version:"2.0.0",title:text(data.get("title")),claim:text(data.get("claim")),risk_score:Number(data.get("risk_score")||0),risk_level:text(data.get("risk_level")),evidence_summary:text(data.get("evidence_summary")),governance_status:text(data.get("governance_status")),required_wording:lines(data.get("required_wording")),disclosures:lines(data.get("disclosures")),reassessment_at:text(data.get("reassessment_at")),classification:"public",public_safe:true,generated_at:new Date().toISOString()
    };
  }
  function markdown(value){
    var out=["# "+value.title,"","## Claim",value.claim,"","## Narrative risk","Score: "+value.risk_score+" · Level: "+value.risk_level,"","## Evidence",value.evidence_summary,"","## Governance",value.governance_status,""];
    if(value.required_wording.length){out.push("## Required wording");value.required_wording.forEach(function(x){out.push("- "+x);});out.push("");}
    if(value.disclosures.length){out.push("## Disclosures");value.disclosures.forEach(function(x){out.push("- "+x);});out.push("");}
    out.push("## Reassessment",value.reassessment_at||"Not scheduled","");return out.join("\n");
  }
  function html(value){return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\"><title>"+escapeHtml(value.title)+"</title></head><body><main><h1>"+escapeHtml(value.title)+"</h1><h2>Claim</h2><p>"+escapeHtml(value.claim)+"</p><h2>Narrative risk</h2><p>Score: "+value.risk_score+" · Level: "+escapeHtml(value.risk_level)+"</p><h2>Evidence</h2><p>"+escapeHtml(value.evidence_summary)+"</p><h2>Governance</h2><p>"+escapeHtml(value.governance_status)+"</p><h2>Disclosures</h2><ul>"+value.disclosures.map(function(x){return "<li>"+escapeHtml(x)+"</li>";}).join("")+"</ul></main></body></html>";}
  function download(name,content,type){var blob=new Blob([content],{type:type});var url=URL.createObjectURL(blob);var a=document.createElement("a");a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);}
  document.querySelectorAll("[data-cnrisk-publication]").forEach(function(root){
    var form=root.querySelector("form"),preview=root.querySelector("[data-cnrisk-publication-preview]"),current=null;
    function render(){current=payload(form);preview.innerHTML="<h3>"+escapeHtml(current.title||"Untitled briefing")+"</h3><p><strong>Claim:</strong> "+escapeHtml(current.claim)+"</p><p><strong>Risk:</strong> "+current.risk_score+" · "+escapeHtml(current.risk_level)+"</p><p><strong>Evidence:</strong> "+escapeHtml(current.evidence_summary)+"</p><p><strong>Governance:</strong> "+escapeHtml(current.governance_status)+"</p><p><strong>Disclosures:</strong> "+escapeHtml(current.disclosures.join("; ")||"None recorded")+"</p>";}
    form.addEventListener("submit",function(event){event.preventDefault();render();});
    root.querySelectorAll("[data-cnrisk-download-format]").forEach(function(button){button.addEventListener("click",function(){if(!current){render();}var format=button.getAttribute("data-cnrisk-download-format"),slug=slugify(current.title);if(format==="json"){download(slug+".json",JSON.stringify(current,null,2)+"\n","application/json");}else if(format==="html"){download(slug+".html",html(current),"text/html");}else{download(slug+".md",markdown(current),"text/markdown");}});});
    render();
  });
})();
